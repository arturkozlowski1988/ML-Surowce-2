"""
Prediction ViewModel - MVVM layer for forecasting functionality.
Encapsulates all ML model training, prediction, and state management.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.viewmodels.base_viewmodel import BaseViewModel, ViewModelState

logger = logging.getLogger("PredictionViewModel")


class ModelType(Enum):
    """Available forecasting models."""

    BASELINE = "baseline"
    RANDOM_FOREST = "rf"
    GRADIENT_BOOSTING = "gb"
    EXPONENTIAL_SMOOTHING = "es"
    LSTM = "lstm"  # Deep Learning


@dataclass
class ModelResult:
    """Result of model training and prediction."""

    model_type: ModelType
    model_name: str
    predictions: pd.DataFrame
    training_time_ms: float
    metrics: dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.error is None and not self.predictions.empty


@dataclass
class PredictionState(ViewModelState):
    """State for Prediction ViewModel."""

    df_historical: Optional[pd.DataFrame] = None
    df_prepared: Optional[pd.DataFrame] = None
    current_product_id: Optional[int] = None
    current_model: Optional[ModelType] = None
    model_results: dict[str, ModelResult] = field(default_factory=dict)
    available_products: list[int] = field(default_factory=list)

    # Progress tracking
    current_step: str = ""
    total_steps: int = 4
    current_step_num: int = 0


class PredictionViewModel(BaseViewModel):
    """
    ViewModel for Prediction/Forecasting module.

    Responsibilities:
    - Load and preprocess historical data
    - Train ML models with progress tracking
    - Generate forecasts
    - Cache results for performance
    - Provide metrics and diagnostics
    """

    MODEL_NAMES = {
        ModelType.BASELINE: "Baseline (SMA-4)",
        ModelType.RANDOM_FOREST: "Random Forest",
        ModelType.GRADIENT_BOOSTING: "Gradient Boosting",
        ModelType.EXPONENTIAL_SMOOTHING: "Exponential Smoothing",
        ModelType.LSTM: "LSTM (Deep Learning)",
    }

    def __init__(self, db, forecaster, prepare_time_series, fill_missing_weeks):
        super().__init__(db)
        self.forecaster = forecaster
        self.prepare_time_series = prepare_time_series
        self.fill_missing_weeks = fill_missing_weeks
        self._state = PredictionState()

    @property
    def prediction_state(self) -> PredictionState:
        return self._state

    def load_data(self, force_refresh: bool = False) -> bool:
        """
        Load and prepare historical data.

        Args:
            force_refresh: Force reload from database

        Returns:
            True if data loaded successfully
        """
        cache_key = "historical_data"

        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                self._state.df_prepared = cached
                self._state.available_products = list(cached["TowarId"].unique())
                self._set_success()
                return True

        try:
            # Step 1: Load raw data
            self._update_step(1, "Pobieranie danych z bazy...")
            df_raw = self.db.get_historical_data()

            if df_raw.empty:
                self._set_error("Brak danych historycznych w bazie")
                return False

            self._state.df_historical = df_raw

            # Step 2: Prepare time series
            self._update_step(2, "Konwersja na szeregi czasowe...")
            df_clean = self.prepare_time_series(df_raw)

            # Step 3: Fill missing weeks
            self._update_step(3, "Uzupełnianie brakujących tygodni...")
            df_full = self.fill_missing_weeks(df_clean)

            self._state.df_prepared = df_full
            self._state.available_products = list(df_full["TowarId"].unique())

            # Cache result
            self._set_cached(cache_key, df_full)

            self._update_step(4, "Dane gotowe")
            self._set_success()

            logger.info(f"Loaded {len(df_full)} rows, {len(self._state.available_products)} products")
            return True

        except Exception as e:
            self._set_error(f"Błąd ładowania danych: {e}")
            return False

    def _update_step(self, step_num: int, message: str):
        """Update loading step."""
        self._state.current_step_num = step_num
        self._state.current_step = message
        progress = step_num / self._state.total_steps
        self._set_loading(progress, message)

    def train_model(self, product_id: int, model_type: ModelType, weeks_ahead: int = 4) -> ModelResult:
        """
        Train a specific model and generate predictions.

        Args:
            product_id: Product ID to forecast
            model_type: Type of model to train
            weeks_ahead: Number of weeks to forecast

        Returns:
            ModelResult with predictions and metrics
        """
        # Check cache
        cache_key = f"{product_id}_{model_type.value}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if self._state.df_prepared is None:
            return ModelResult(
                model_type=model_type,
                model_name=self.MODEL_NAMES[model_type],
                predictions=pd.DataFrame(),
                training_time_ms=0,
                error="No data loaded",
            )

        self._state.current_product_id = product_id
        self._state.current_model = model_type

        try:
            start_time = time.time()

            # Get product data
            df_product = self._state.df_prepared[self._state.df_prepared["TowarId"] == product_id]

            if len(df_product) < 8:
                return ModelResult(
                    model_type=model_type,
                    model_name=self.MODEL_NAMES[model_type],
                    predictions=pd.DataFrame(),
                    training_time_ms=0,
                    error=f"Niewystarczające dane ({len(df_product)} < 8 tygodni)",
                )

            # Train and predict
            if model_type == ModelType.BASELINE:
                predictions = self.forecaster.predict_baseline(df_product, weeks_ahead)
            else:
                predictions = self.forecaster.train_predict(
                    df_product, weeks_ahead=weeks_ahead, model_type=model_type.value
                )

            training_time = (time.time() - start_time) * 1000

            # Calculate metrics
            metrics = self._calculate_metrics(df_product, predictions)

            result = ModelResult(
                model_type=model_type,
                model_name=self.MODEL_NAMES[model_type],
                predictions=predictions,
                training_time_ms=training_time,
                metrics=metrics,
            )

            # Cache result
            self._set_cached(cache_key, result)
            self._state.model_results[cache_key] = result

            logger.info(f"Trained {model_type.value} for product {product_id} in {training_time:.0f}ms")
            return result

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return ModelResult(
                model_type=model_type,
                model_name=self.MODEL_NAMES[model_type],
                predictions=pd.DataFrame(),
                training_time_ms=0,
                error=str(e),
            )

    def _calculate_metrics(self, df_historical: pd.DataFrame, df_predictions: pd.DataFrame) -> dict[str, float]:
        """Calculate forecast quality metrics."""
        metrics = {}

        try:
            # Recent history statistics
            recent_qty = df_historical["Quantity"].tail(4).values

            if len(recent_qty) > 0:
                metrics["avg_recent"] = float(np.mean(recent_qty))
                metrics["std_recent"] = float(np.std(recent_qty))
                metrics["trend"] = float(recent_qty[-1] - recent_qty[0]) if len(recent_qty) > 1 else 0.0

            # Prediction statistics
            if not df_predictions.empty:
                pred_qty = df_predictions["Predicted_Qty"].values
                metrics["avg_forecast"] = float(np.mean(pred_qty))
                metrics["forecast_change_pct"] = (
                    (
                        (metrics.get("avg_forecast", 0) - metrics.get("avg_recent", 0))
                        / max(metrics.get("avg_recent", 1), 0.001)
                        * 100
                    )
                    if "avg_recent" in metrics
                    else 0.0
                )

        except Exception as e:
            logger.warning(f"Metrics calculation failed: {e}")

        return metrics

    def get_combined_forecast_data(
        self, product_id: int, model_type: ModelType, start_date=None, end_date=None
    ) -> pd.DataFrame:
        """
        Get combined historical + forecast data for charting.

        Returns DataFrame with columns: Date, Quantity, Type
        """
        if self._state.df_prepared is None:
            return pd.DataFrame()

        # Get historical data
        hist_data = self._state.df_prepared[self._state.df_prepared["TowarId"] == product_id].copy()
        hist_data["Type"] = "History"

        # Get baseline predictions
        baseline_result = self.train_model(product_id, ModelType.BASELINE)
        baseline_data = pd.DataFrame()
        if baseline_result.is_valid:
            baseline_data = baseline_result.predictions.copy()
            baseline_data["Type"] = "Forecast (Baseline)"
            baseline_data = baseline_data.rename(columns={"Predicted_Qty": "Quantity"})

        # Get selected model predictions
        model_result = self.train_model(product_id, model_type)
        model_data = pd.DataFrame()
        if model_result.is_valid:
            model_data = model_result.predictions.copy()
            model_data["Type"] = f"Forecast ({model_result.model_name})"
            model_data = model_data.rename(columns={"Predicted_Qty": "Quantity"})

        # Combine
        combined = pd.concat(
            [
                hist_data[["Date", "Quantity", "Type"]],
                baseline_data[["Date", "Quantity", "Type"]] if not baseline_data.empty else pd.DataFrame(),
                model_data[["Date", "Quantity", "Type"]] if not model_data.empty else pd.DataFrame(),
            ],
            ignore_index=True,
        )

        # Apply date filter
        if start_date and end_date and not combined.empty:
            mask = (combined["Date"].dt.date >= start_date) & (combined["Date"].dt.date <= end_date)
            combined = combined[mask]

        return combined

    def get_model_diagnostics(self, product_id: int, model_type: ModelType) -> dict[str, Any]:
        """Get detailed diagnostics for a trained model."""
        cache_key = f"{product_id}_{model_type.value}"

        if cache_key not in self._state.model_results:
            return {"error": "Model not trained"}

        result = self._state.model_results[cache_key]

        return {
            "model_name": result.model_name,
            "training_time_ms": result.training_time_ms,
            "predictions_count": len(result.predictions),
            "metrics": result.metrics,
            "is_valid": result.is_valid,
            "error": result.error,
        }
