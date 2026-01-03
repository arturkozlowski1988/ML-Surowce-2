import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from joblib import Parallel, delayed
import warnings
import logging

# Optional: Polish holidays fallback if database not available
try:
    import holidays
    PL_HOLIDAYS_FALLBACK = holidays.Poland()
except ImportError:
    PL_HOLIDAYS_FALLBACK = None
    
# Suppress warnings for cleaner logs
warnings.filterwarnings("ignore")

logger = logging.getLogger('Forecaster')

class Forecaster:
    def __init__(self, cti_holidays_set: set = None):
        """
        Initialize Forecaster with optional CTI holidays.
        
        Args:
            cti_holidays_set: Set of datetime.date objects from CtiHolidays table.
                             If None, falls back to holidays library.
                             Get via: db.get_cti_holidays_set()
        """
        self.models = {}
        self._cti_holidays = cti_holidays_set  # Company holidays from database

    def predict_baseline(self, df: pd.DataFrame, weeks_ahead: int = 4) -> pd.DataFrame:
        """
        Simple Moving Average (SMA) baseline model.
        Uses last 4 weeks average to predict next weeks.
        """
        df = df.copy()
        predictions = []
        
        # We need to process each product separately
        for product_id in df['TowarId'].unique():
            prod_df = df[df['TowarId'] == product_id].sort_values('Date')
            
            if len(prod_df) < 4:
                continue
                
            last_4_weeks_avg = prod_df['Quantity'].tail(4).mean()
            
            # Predict ahead
            last_date = prod_df['Date'].max()
            for i in range(1, weeks_ahead + 1):
                future_date = last_date + pd.Timedelta(weeks=i)
                predictions.append({
                    'TowarId': product_id,
                    'Date': future_date,
                    'Predicted_Qty': last_4_weeks_avg,
                    'Model': 'Baseline (SMA-4)'
                })
                
        return pd.DataFrame(predictions)

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Shared feature engineering for ML models.
        Uses company holidays from CtiHolidays (preferred) or holidays library (fallback).
        """
        df = df.copy()
        df['WeekOfYear'] = df['Date'].dt.isocalendar().week
        df['Month'] = df['Date'].dt.month
        
        # Holiday detection: Priority 1 = CtiHolidays from database, Priority 2 = holidays library
        if self._cti_holidays is not None and len(self._cti_holidays) > 0:
            # Use company-specific holidays from database (more accurate, includes Easter)
            df['IsHoliday'] = df['Date'].apply(
                lambda x: 1 if x.date() in self._cti_holidays else 0
            )
        elif PL_HOLIDAYS_FALLBACK is not None:
            # Fallback to holidays library
            df['IsHoliday'] = df['Date'].apply(
                lambda x: 1 if x in PL_HOLIDAYS_FALLBACK else 0
            )
        else:
            df['IsHoliday'] = 0
        
        # Lags and Rolling
        df['Lag_1'] = df.groupby('TowarId')['Quantity'].shift(1)
        df['Lag_2'] = df.groupby('TowarId')['Quantity'].shift(2)
        df['Lag_3'] = df.groupby('TowarId')['Quantity'].shift(3)
        df['Rolling_Mean_4'] = df.groupby('TowarId')['Quantity'].transform(lambda x: x.rolling(window=4).mean())
        
        return df.dropna()

    def _train_predict_single_ml(self, df: pd.DataFrame, product_id, model_type: str, weeks_ahead: int) -> list:
        """
        Helper to train and predict for a single product using Recursive Multi-step strategy.
        """
        prod_df = df[df['TowarId'] == product_id].sort_values('Date')
        
        # Minimum data requirement for ML
        if len(prod_df) < 8: 
            return []

        # Prepare features
        prod_feat_df = self._prepare_features(prod_df)
        if prod_feat_df.empty:
            return []

        features = ['WeekOfYear', 'Month', 'IsHoliday', 'Lag_1', 'Lag_2', 'Lag_3', 'Rolling_Mean_4']
        target = 'Quantity'

        X = prod_feat_df[features]
        y = prod_feat_df[target]

        # Model Selection
        if model_type == 'gb':
            model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        else: # Default to Random Forest
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            
        model.fit(X, y)

        # Recursive Prediction
        predictions = []
        
        # Initial state for recursion
        last_row = prod_df.iloc[-1]
        
        # Note: We need the ACTUAL values (or best estimates) for init lags, not from feature DF which might end earlier
        # But we can grab them from tail of prod_df
        current_lags = prod_df['Quantity'].tail(3).tolist()[::-1] # [t-1, t-2, t-3]
        if len(current_lags) < 3: return [] # Should not happen due to min len check
        
        last_date = last_row['Date']
        
        for i in range(1, weeks_ahead + 1):
            future_date = last_date + pd.Timedelta(weeks=i)
            week_of_year = future_date.isocalendar()[1]
            month = future_date.month
            
            # Approximate rolling mean for future steps (using known history + preds)
            rolling_mean = np.mean([current_lags[0]] + current_lags[:3]) # Simplification
            
            # Check if future date is a holiday (CtiHolidays first, then fallback)
            if self._cti_holidays is not None and len(self._cti_holidays) > 0:
                is_holiday = 1 if future_date.date() in self._cti_holidays else 0
            elif PL_HOLIDAYS_FALLBACK is not None:
                is_holiday = 1 if future_date in PL_HOLIDAYS_FALLBACK else 0
            else:
                is_holiday = 0
            
            # Build Row
            feat_dict = {
                'WeekOfYear': [week_of_year],
                'Month': [month],
                'IsHoliday': [is_holiday],
                'Lag_1': [current_lags[0]],
                'Lag_2': [current_lags[1]],
                'Lag_3': [current_lags[2]],
                'Rolling_Mean_4': [rolling_mean]
            }
            
            X_future = pd.DataFrame(feat_dict)
            pred_qty = model.predict(X_future)[0]
            pred_qty = max(0, pred_qty) # ReLU
            
            predictions.append({
                'TowarId': product_id,
                'Date': future_date,
                'Predicted_Qty': pred_qty,
                'Model': 'Gradient Boosting' if model_type == 'gb' else 'Random Forest'
            })
            
            # Update Lags: [new_pred, t-1, t-2]
            current_lags = [pred_qty] + current_lags[:-1]
            
        return predictions

    def _train_predict_exponential_smoothing(self, df: pd.DataFrame, product_id, weeks_ahead: int) -> list:
        """
        Holt-Winters Exponential Smoothing.
        Good for trend and seasonality.
        """
        prod_df = df[df['TowarId'] == product_id].sort_values('Date')
        
        if len(prod_df) < 5: 
            return []
            
        # Re-index to ensure freq (filled weeks in preprocessing helpful here)
        prod_df = prod_df.set_index('Date')
        series = prod_df['Quantity'].asfreq('W-SUN').fillna(0)
        
        try:
            # We try Additive Trend and Additive Seasonality (if enough data)
            # If data is short, simple ES or Holt
            if len(series) >= 12: # Enough for seasonality?
                model = ExponentialSmoothing(series, trend='add', seasonal='add', seasonal_periods=4).fit()
            else:
                model = ExponentialSmoothing(series, trend='add', seasonal=None).fit()
                
            forecast = model.forecast(weeks_ahead)
            
            predictions = []
            for date, qty in forecast.items():
                predictions.append({
                    'TowarId': product_id,
                    'Date': date,
                    'Predicted_Qty': max(0, qty),
                    'Model': 'Exponential Smoothing'
                })
            return predictions
        except Exception as e:
            # print(f"ES Error for {product_id}: {e}") # Debug
            return []

    def train_predict(self, df: pd.DataFrame, weeks_ahead: int = 4, model_type: str = 'rf') -> pd.DataFrame:
        """
        Universal entry point for forecasting.
        model_type: 'rf' (RandomForest), 'gb' (GradientBoosting), 'es' (ExponentialSmoothing)
        
        PERFORMANCE: Uses parallel processing via joblib for multi-core execution.
        Target: < 10s for 100 SKU (previously > 30s with sequential loop)
        """
        product_ids = df['TowarId'].unique()
        n_products = len(product_ids)
        
        logger.info(f"Starting parallel forecasting for {n_products} products using model '{model_type}'")
        
        # Define processing function for parallel execution
        def process_product(pid):
            try:
                if model_type == 'es':
                    return self._train_predict_exponential_smoothing(df, pid, weeks_ahead)
                else:
                    return self._train_predict_single_ml(df, pid, model_type, weeks_ahead)
            except Exception as e:
                logger.warning(f"Error forecasting product {pid}: {e}")
                return []
        
        # Use parallel processing with threads (prefer="threads" for I/O bound, 
        # n_jobs=-1 uses all available cores)
        # For small datasets (< 5 products), sequential is faster due to overhead
        if n_products < 5:
            # Sequential for small datasets
            results = [process_product(pid) for pid in product_ids]
        else:
            # Parallel execution for larger datasets
            results = Parallel(n_jobs=-1, prefer="threads", verbose=0)(
                delayed(process_product)(pid) for pid in product_ids
            )
        
        # Flatten results
        predictions = []
        for result in results:
            predictions.extend(result)
        
        logger.info(f"Forecasting complete: {len(predictions)} predictions generated")
        
        return pd.DataFrame(predictions)

