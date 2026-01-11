"""
Forecast Accuracy Tests.
Backtests forecasting models against historical data.
"""

import numpy as np
import pandas as pd
import pytest


class TestForecastLogic:
    """Test forecasting calculation logic."""

    def test_sma4_calculation_correctness(self):
        """SMA-4 should correctly average last 4 values."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        # Create test data with known values
        rows = []
        for week in range(1, 9):  # 8 weeks
            rows.append(
                {
                    "TowarId": 1,
                    "Year": 2024,
                    "Week": week,
                    "Quantity": week * 10,  # 10, 20, 30, 40, 50, 60, 70, 80
                }
            )

        df = pd.DataFrame(rows)
        df = prepare_time_series(df)
        df = fill_missing_weeks(df)

        forecaster = Forecaster()
        predictions = forecaster.predict_baseline(df, weeks_ahead=1)

        # SMA-4 of [50, 60, 70, 80] = (50+60+70+80)/4 = 65
        assert len(predictions) == 1
        assert abs(predictions.iloc[0]["Predicted_Qty"] - 65.0) < 1.0

    def test_predictions_are_non_negative(self):
        """Predictions should never be negative."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        np.random.seed(42)
        rows = []
        for week in range(1, 53):
            rows.append({"TowarId": 1, "Year": 2024, "Week": week, "Quantity": max(0, np.random.normal(50, 30))})

        df = pd.DataFrame(rows)
        df = prepare_time_series(df)
        df = fill_missing_weeks(df)

        forecaster = Forecaster()

        for model_type in ["rf", "gb", "es"]:
            predictions = forecaster.train_predict(df, weeks_ahead=4, model_type=model_type)
            if not predictions.empty:
                assert (predictions["Predicted_Qty"] >= 0).all(), f"Model {model_type} produced negative predictions"


@pytest.mark.integration
@pytest.mark.slow
class TestForecastAccuracyBacktest:
    """Backtest forecasting against real historical data."""

    def test_baseline_mape_below_threshold(self):
        """Baseline model MAPE should be below 50% on stable products."""
        from src.db_connector import DatabaseConnector
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        try:
            db = DatabaseConnector(enable_audit=False)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

        # Get full year of data
        historical = db.get_historical_data(date_from="2024-01-01", date_to="2024-12-31")

        if historical.empty or len(historical) < 40:
            pytest.skip("Insufficient historical data for backtest")

        # Filter to products with consistent data
        product_counts = historical.groupby("TowarId").size()
        stable_products = product_counts[product_counts >= 40].index.tolist()

        if not stable_products:
            pytest.skip("No products with sufficient data")

        # Test on first stable product
        test_product = stable_products[0]
        df = historical[historical["TowarId"] == test_product].copy()

        df = prepare_time_series(df)
        df = fill_missing_weeks(df)

        # Split: train on first 80%, test on last 20%
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        forecaster = Forecaster()
        predictions = forecaster.predict_baseline(train_df, weeks_ahead=len(test_df))

        if predictions.empty:
            pytest.skip("No predictions generated")

        # Calculate MAPE
        merged = predictions.merge(test_df[["Date", "Quantity"]], on="Date", how="inner")

        if merged.empty:
            pytest.skip("No overlapping dates for comparison")

        mape = (
            abs(merged["Predicted_Qty"] - merged["Quantity"]) / merged["Quantity"].replace(0, np.nan)
        ).dropna().mean() * 100

        assert mape < 50, f"Baseline MAPE {mape:.1f}% exceeds 50% threshold"
