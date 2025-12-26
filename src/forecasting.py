import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings

# Suppress warnings for cleaner logs
warnings.filterwarnings("ignore")

class Forecaster:
    def __init__(self):
        self.models = {}

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
        """
        df = df.copy()
        df['WeekOfYear'] = df['Date'].dt.isocalendar().week
        df['Month'] = df['Date'].dt.month
        
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

        features = ['WeekOfYear', 'Month', 'Lag_1', 'Lag_2', 'Lag_3', 'Rolling_Mean_4']
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
            
            # Build Row
            feat_dict = {
                'WeekOfYear': [week_of_year],
                'Month': [month],
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
        """
        predictions = []
        product_ids = df['TowarId'].unique()
        
        for pid in product_ids:
            if model_type == 'es':
                preds = self._train_predict_exponential_smoothing(df, pid, weeks_ahead)
            else:
                 # ML Types: rf, gb
                preds = self._train_predict_single_ml(df, pid, model_type, weeks_ahead)
                
            predictions.extend(preds)
            
        return pd.DataFrame(predictions)
