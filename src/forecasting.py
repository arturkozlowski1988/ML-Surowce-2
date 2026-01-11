"""
Forecasting module for AI Supply Assistant.

Provides ML models for demand forecasting:
- Baseline (SMA-4)
- Random Forest
- Gradient Boosting
- Exponential Smoothing (Holt-Winters)
- LSTM (Deep Learning)

Enhanced with:
- Configurable hyperparameters from ml_config
- Model evaluation metrics (MAPE, RMSE, MAE, R²)
- Model persistence support
"""

import logging
import warnings
from typing import Any, Optional

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Optional: Polish holidays fallback if database not available
try:
    import holidays

    PL_HOLIDAYS_FALLBACK = holidays.Poland()
except ImportError:
    PL_HOLIDAYS_FALLBACK = None

# Optional: TensorFlow for LSTM
try:
    import tensorflow as tf
    from tensorflow import keras

    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

# Suppress warnings for cleaner logs
warnings.filterwarnings("ignore")

logger = logging.getLogger("Forecaster")


def mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Oblicza MAPE (Mean Absolute Percentage Error).

    MAPE = (1/n) * Σ|y_true - y_pred| / |y_true| * 100%

    Returns:
        MAPE as percentage (e.g., 15.5 means 15.5%)
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    # Avoid division by zero
    mask = y_true != 0
    if not mask.any():
        return 0.0

    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


class Forecaster:
    """
    Klasa do prognozowania popytu na surowce.

    Obsługuje modele:
    - baseline: Prosta średnia krocząca (SMA-4)
    - rf: Random Forest Regressor
    - gb: Gradient Boosting Regressor
    - es: Exponential Smoothing (Holt-Winters)
    - lstm: LSTM Neural Network (Deep Learning)

    Usage:
        forecaster = Forecaster()
        predictions = forecaster.train_predict(df, weeks_ahead=4, model_type='rf')
        metrics = forecaster.get_last_metrics()
    """

    def __init__(self, cti_holidays_set: set = None, config: dict[str, Any] = None):
        """
        Initialize Forecaster with optional CTI holidays and config.

        Args:
            cti_holidays_set: Set of datetime.date objects from CtiHolidays table.
                             If None, falls back to holidays library.
                             Get via: db.get_cti_holidays_set()
            config: Optional configuration dict. If None, loads from ml_config.
        """
        self.models = {}
        self._cti_holidays = cti_holidays_set
        self._last_metrics: dict[str, float] = {}
        self._last_model = None  # Store last trained model for persistence
        self._scaler = None  # For LSTM normalization

        # Load config
        if config is None:
            try:
                from src.ml_config import load_config

                self._config = load_config()
            except ImportError:
                self._config = None
        else:
            self._config = config

    def predict_baseline(self, df: pd.DataFrame, weeks_ahead: int = 4) -> pd.DataFrame:
        """
        Simple Moving Average (SMA) baseline model.
        Uses last 4 weeks average to predict next weeks.
        """
        df = df.copy()
        predictions = []

        for product_id in df["TowarId"].unique():
            prod_df = df[df["TowarId"] == product_id].sort_values("Date")

            if len(prod_df) < 4:
                continue

            last_4_weeks_avg = prod_df["Quantity"].tail(4).mean()

            last_date = prod_df["Date"].max()
            for i in range(1, weeks_ahead + 1):
                future_date = last_date + pd.Timedelta(weeks=i)
                predictions.append(
                    {
                        "TowarId": product_id,
                        "Date": future_date,
                        "Predicted_Qty": last_4_weeks_avg,
                        "Model": "Baseline (SMA-4)",
                    }
                )

        return pd.DataFrame(predictions)

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Shared feature engineering for ML models.
        Uses company holidays from CtiHolidays (preferred) or holidays library (fallback).
        """
        df = df.copy()
        df["WeekOfYear"] = df["Date"].dt.isocalendar().week
        df["Month"] = df["Date"].dt.month

        # Holiday detection
        if self._cti_holidays is not None and len(self._cti_holidays) > 0:
            df["IsHoliday"] = df["Date"].apply(lambda x: 1 if x.date() in self._cti_holidays else 0)
        elif PL_HOLIDAYS_FALLBACK is not None:
            df["IsHoliday"] = df["Date"].apply(lambda x: 1 if x in PL_HOLIDAYS_FALLBACK else 0)
        else:
            df["IsHoliday"] = 0

        # Lags and Rolling
        df["Lag_1"] = df.groupby("TowarId")["Quantity"].shift(1)
        df["Lag_2"] = df.groupby("TowarId")["Quantity"].shift(2)
        df["Lag_3"] = df.groupby("TowarId")["Quantity"].shift(3)
        df["Rolling_Mean_4"] = df.groupby("TowarId")["Quantity"].transform(lambda x: x.rolling(window=4).mean())

        return df.dropna()

    def _get_model_params(self, model_type: str) -> dict[str, Any]:
        """Get model parameters from config."""
        if self._config is None:
            # Default params
            defaults = {
                "rf": {"n_estimators": 100, "random_state": 42},
                "gb": {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 3, "random_state": 42},
                "es": {"trend": "add", "seasonal": "add", "seasonal_periods": 4},
                "lstm": {"units": 64, "epochs": 50, "batch_size": 32, "dropout": 0.2, "lookback": 8},
            }
            return defaults.get(model_type, {})

        try:
            from src.ml_config import MLConfig, get_model_config

            # Convert dict to MLConfig if needed
            if isinstance(self._config, dict):
                config_obj = MLConfig.from_dict(self._config)
            else:
                config_obj = self._config

            return get_model_config(model_type, config_obj)
        except ImportError:
            return {}

    def _train_predict_single_ml(
        self, df: pd.DataFrame, product_id, model_type: str, weeks_ahead: int
    ) -> tuple[list, Optional[Any]]:
        """
        Train and predict for a single product using Recursive Multi-step strategy.
        Returns (predictions, trained_model).
        """
        prod_df = df[df["TowarId"] == product_id].sort_values("Date")

        if len(prod_df) < 8:
            return [], None

        prod_feat_df = self._prepare_features(prod_df)
        if prod_feat_df.empty:
            return [], None

        features = ["WeekOfYear", "Month", "IsHoliday", "Lag_1", "Lag_2", "Lag_3", "Rolling_Mean_4"]
        target = "Quantity"

        X = prod_feat_df[features]
        y = prod_feat_df[target]

        # Get model params from config
        params = self._get_model_params(model_type)

        # Model Selection with configurable params
        if model_type == "gb":
            model = GradientBoostingRegressor(
                n_estimators=params.get("n_estimators", 100),
                learning_rate=params.get("learning_rate", 0.1),
                max_depth=params.get("max_depth", 3),
                min_samples_split=params.get("min_samples_split", 2),
                subsample=params.get("subsample", 1.0),
                random_state=params.get("random_state", 42),
            )
        else:  # Default to Random Forest
            model = RandomForestRegressor(
                n_estimators=params.get("n_estimators", 100),
                max_depth=params.get("max_depth", None),
                min_samples_split=params.get("min_samples_split", 2),
                min_samples_leaf=params.get("min_samples_leaf", 1),
                random_state=params.get("random_state", 42),
            )

        model.fit(X, y)

        # Recursive Prediction
        predictions = []
        current_lags = prod_df["Quantity"].tail(3).tolist()[::-1]
        if len(current_lags) < 3:
            return [], None

        last_date = prod_df.iloc[-1]["Date"]

        for i in range(1, weeks_ahead + 1):
            future_date = last_date + pd.Timedelta(weeks=i)
            week_of_year = future_date.isocalendar()[1]
            month = future_date.month
            rolling_mean = np.mean([current_lags[0]] + current_lags[:3])

            if self._cti_holidays is not None and len(self._cti_holidays) > 0:
                is_holiday = 1 if future_date.date() in self._cti_holidays else 0
            elif PL_HOLIDAYS_FALLBACK is not None:
                is_holiday = 1 if future_date in PL_HOLIDAYS_FALLBACK else 0
            else:
                is_holiday = 0

            feat_dict = {
                "WeekOfYear": [week_of_year],
                "Month": [month],
                "IsHoliday": [is_holiday],
                "Lag_1": [current_lags[0]],
                "Lag_2": [current_lags[1]],
                "Lag_3": [current_lags[2]],
                "Rolling_Mean_4": [rolling_mean],
            }

            X_future = pd.DataFrame(feat_dict)
            pred_qty = model.predict(X_future)[0]
            pred_qty = max(0, pred_qty)

            predictions.append(
                {
                    "TowarId": product_id,
                    "Date": future_date,
                    "Predicted_Qty": pred_qty,
                    "Model": "Gradient Boosting" if model_type == "gb" else "Random Forest",
                }
            )

            current_lags = [pred_qty] + current_lags[:-1]

        return predictions, model

    def _train_predict_exponential_smoothing(
        self, df: pd.DataFrame, product_id, weeks_ahead: int
    ) -> tuple[list, Optional[Any]]:
        """
        Holt-Winters Exponential Smoothing.
        Good for trend and seasonality.
        """
        prod_df = df[df["TowarId"] == product_id].sort_values("Date")

        if len(prod_df) < 5:
            return [], None

        prod_df = prod_df.set_index("Date")
        series = prod_df["Quantity"].asfreq("W-SUN").fillna(0)

        params = self._get_model_params("es")

        try:
            if len(series) >= 12:
                model = ExponentialSmoothing(
                    series,
                    trend=params.get("trend", "add"),
                    seasonal=params.get("seasonal", "add"),
                    seasonal_periods=params.get("seasonal_periods", 4),
                    damped_trend=params.get("damped_trend", False),
                ).fit()
            else:
                model = ExponentialSmoothing(series, trend=params.get("trend", "add"), seasonal=None).fit()

            forecast = model.forecast(weeks_ahead)

            predictions = []
            for date, qty in forecast.items():
                predictions.append(
                    {
                        "TowarId": product_id,
                        "Date": date,
                        "Predicted_Qty": max(0, qty),
                        "Model": "Exponential Smoothing",
                    }
                )
            return predictions, model

        except Exception as e:
            logger.warning(f"ES Error for {product_id}: {e}")
            return [], None

    def _train_predict_lstm(self, df: pd.DataFrame, product_id, weeks_ahead: int) -> tuple[list, Optional[Any]]:
        """
        LSTM Neural Network for time series forecasting.
        Requires TensorFlow.
        """
        if not TF_AVAILABLE:
            logger.warning("TensorFlow not available. Cannot use LSTM model.")
            return [], None

        prod_df = df[df["TowarId"] == product_id].sort_values("Date")

        params = self._get_model_params("lstm")
        lookback = params.get("lookback", 8)

        if len(prod_df) < lookback + weeks_ahead:
            return [], None

        try:
            # Prepare data
            values = prod_df["Quantity"].values.reshape(-1, 1)

            # Normalize
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_values = scaler.fit_transform(values)
            self._scaler = scaler

            # Create sequences
            X, y = [], []
            for i in range(lookback, len(scaled_values)):
                X.append(scaled_values[i - lookback : i, 0])
                y.append(scaled_values[i, 0])

            X, y = np.array(X), np.array(y)
            X = X.reshape((X.shape[0], X.shape[1], 1))

            # Build model
            model = keras.Sequential(
                [
                    keras.layers.LSTM(params.get("units", 64), return_sequences=True, input_shape=(lookback, 1)),
                    keras.layers.Dropout(params.get("dropout", 0.2)),
                    keras.layers.LSTM(params.get("units_second", 32), return_sequences=False),
                    keras.layers.Dropout(params.get("dropout", 0.2)),
                    keras.layers.Dense(32, activation="relu"),
                    keras.layers.Dense(1),
                ]
            )

            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=params.get("learning_rate", 0.001)),
                loss="mse",
                metrics=["mae"],
            )

            # Train with early stopping
            early_stop = keras.callbacks.EarlyStopping(monitor="loss", patience=10, restore_best_weights=True)

            model.fit(
                X,
                y,
                epochs=params.get("epochs", 50),
                batch_size=params.get("batch_size", 32),
                callbacks=[early_stop],
                verbose=0,
            )

            # Recursive prediction
            predictions = []
            current_sequence = scaled_values[-lookback:].flatten().tolist()
            last_date = prod_df["Date"].max()

            for i in range(1, weeks_ahead + 1):
                future_date = last_date + pd.Timedelta(weeks=i)

                # Prepare input
                X_pred = np.array(current_sequence[-lookback:]).reshape(1, lookback, 1)

                # Predict
                pred_scaled = model.predict(X_pred, verbose=0)[0, 0]
                pred_qty = scaler.inverse_transform([[pred_scaled]])[0, 0]
                pred_qty = max(0, pred_qty)

                predictions.append(
                    {
                        "TowarId": product_id,
                        "Date": future_date,
                        "Predicted_Qty": pred_qty,
                        "Model": "LSTM (Deep Learning)",
                    }
                )

                # Update sequence
                current_sequence.append(pred_scaled)

            return predictions, model

        except Exception as e:
            logger.error(f"LSTM Error for {product_id}: {e}")
            return [], None

    def train_predict(self, df: pd.DataFrame, weeks_ahead: int = 4, model_type: str = "rf") -> pd.DataFrame:
        """
        Universal entry point for forecasting.

        Args:
            df: DataFrame with columns ['TowarId', 'Date', 'Quantity']
            weeks_ahead: Number of weeks to forecast
            model_type: 'rf', 'gb', 'es', 'lstm'

        Returns:
            DataFrame with predictions
        """
        product_ids = df["TowarId"].unique()
        n_products = len(product_ids)

        logger.info(f"Starting forecasting for {n_products} products using model '{model_type}'")

        def process_product(pid):
            try:
                if model_type == "es":
                    preds, model = self._train_predict_exponential_smoothing(df, pid, weeks_ahead)
                elif model_type == "lstm":
                    preds, model = self._train_predict_lstm(df, pid, weeks_ahead)
                else:
                    preds, model = self._train_predict_single_ml(df, pid, model_type, weeks_ahead)

                # Store last model (for single product case)
                if model is not None and len(product_ids) == 1:
                    self._last_model = model

                return preds

            except Exception as e:
                logger.warning(f"Error forecasting product {pid}: {e}")
                return []

        # LSTM doesn't work well with parallel processing due to TF
        if model_type == "lstm" or n_products < 5:
            results = [process_product(pid) for pid in product_ids]
        else:
            results = Parallel(n_jobs=-1, prefer="threads", verbose=0)(
                delayed(process_product)(pid) for pid in product_ids
            )

        predictions = []
        for result in results:
            predictions.extend(result)

        logger.info(f"Forecasting complete: {len(predictions)} predictions generated")

        return pd.DataFrame(predictions)

    def evaluate_model(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
        """
        Oblicza metryki jakości predykcji.

        Args:
            y_true: Rzeczywiste wartości
            y_pred: Przewidywane wartości

        Returns:
            Dict z metrykami: mape, rmse, mae, r2
        """
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        if len(y_true) == 0 or len(y_pred) == 0:
            return {}

        metrics = {
            "mape": mean_absolute_percentage_error(y_true, y_pred),
            "mae": mean_absolute_error(y_true, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
            "r2": r2_score(y_true, y_pred) if len(y_true) > 1 else 0.0,
        }

        self._last_metrics = metrics
        return metrics

    def cross_validate(
        self, df: pd.DataFrame, product_id: int, model_type: str = "rf", n_folds: int = 5, test_size: int = 4
    ) -> dict[str, float]:
        """
        Przeprowadza walidację krzyżową dla modelu.

        Args:
            df: DataFrame z danymi historycznymi
            product_id: ID produktu
            model_type: Typ modelu
            n_folds: Liczba foldów
            test_size: Rozmiar zbioru testowego (tygodnie)

        Returns:
            Średnie metryki z wszystkich foldów
        """
        prod_df = df[df["TowarId"] == product_id].sort_values("Date")

        if len(prod_df) < test_size * (n_folds + 1):
            logger.warning(f"Not enough data for {n_folds}-fold CV")
            n_folds = max(1, len(prod_df) // (test_size + 8) - 1)

        all_metrics = []

        for fold in range(n_folds):
            # Time series split - always test on future data
            split_point = len(prod_df) - (n_folds - fold) * test_size
            train_df = prod_df.iloc[:split_point]
            test_df = prod_df.iloc[split_point : split_point + test_size]

            if len(train_df) < 8 or len(test_df) < 1:
                continue

            # Train and predict
            predictions = self.train_predict(train_df, weeks_ahead=test_size, model_type=model_type)

            if predictions.empty:
                continue

            # Calculate metrics
            y_true = test_df["Quantity"].values
            y_pred = predictions["Predicted_Qty"].values[: len(y_true)]

            if len(y_pred) == len(y_true):
                fold_metrics = self.evaluate_model(y_true, y_pred)
                all_metrics.append(fold_metrics)

        if not all_metrics:
            return {}

        # Average metrics
        avg_metrics = {}
        for key in all_metrics[0].keys():
            avg_metrics[key] = np.mean([m[key] for m in all_metrics])
            avg_metrics[f"{key}_std"] = np.std([m[key] for m in all_metrics])

        return avg_metrics

    def get_last_metrics(self) -> dict[str, float]:
        """Zwraca metryki z ostatniego treningu."""
        return self._last_metrics

    def get_last_model(self) -> Optional[Any]:
        """Zwraca ostatnio wytrenowany model (do persistence)."""
        return self._last_model

    @staticmethod
    def is_lstm_available() -> bool:
        """Sprawdza czy TensorFlow jest dostępny dla LSTM."""
        return TF_AVAILABLE
