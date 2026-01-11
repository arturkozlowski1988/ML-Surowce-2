"""
ML Pipeline tests for forecasting and preprocessing.
Tests forecasting models, ViewModels, and data preprocessing.

Migrated from scripts/test_ml_pipeline.py to pytest format.
"""

import numpy as np
import pandas as pd
import pytest


class TestPreprocessing:
    """Test data preprocessing functions."""

    def test_prepare_time_series(self, synthetic_time_series):
        """Test time series preparation creates Date column."""
        from src.preprocessing import prepare_time_series

        # Create raw data without Date column
        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)

        assert "Date" in df_ts.columns
        assert not df_ts["Date"].isnull().any()

    def test_fill_missing_weeks(self, synthetic_time_series):
        """Test filling missing weeks in time series."""
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        assert len(df_filled) >= len(df_raw)


class TestForecasterBaseline:
    """Test baseline forecasting model."""

    def test_baseline_prediction_generates_output(self, synthetic_time_series):
        """Test baseline prediction produces non-empty results."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        predictions = forecaster.predict_baseline(df_filled, weeks_ahead=4)

        assert not predictions.empty

    def test_baseline_prediction_has_required_columns(self, synthetic_time_series):
        """Test baseline prediction has required columns."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        predictions = forecaster.predict_baseline(df_filled, weeks_ahead=4)

        expected_cols = {"TowarId", "Date", "Predicted_Qty", "Model"}
        assert expected_cols.issubset(predictions.columns)

    def test_baseline_prediction_count(self, synthetic_time_series):
        """Test correct number of predictions generated."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        weeks_ahead = 4
        predictions = forecaster.predict_baseline(df_filled, weeks_ahead=weeks_ahead)

        n_products = df_raw["TowarId"].nunique()
        expected_preds = n_products * weeks_ahead

        assert len(predictions) == expected_preds

    def test_baseline_no_negative_predictions(self, synthetic_time_series):
        """Test predictions are non-negative."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        predictions = forecaster.predict_baseline(df_filled, weeks_ahead=4)

        assert (predictions["Predicted_Qty"] >= 0).all()


class TestForecasterMLModels:
    """Test ML forecasting models (RF, GB, ES)."""

    @pytest.mark.parametrize(
        "model_type,model_name",
        [
            ("rf", "Random Forest"),
            ("gb", "Gradient Boosting"),
            ("es", "Exponential Smoothing"),
        ],
    )
    def test_ml_model_prediction(self, synthetic_time_series, model_type, model_name):
        """Test ML model predictions are valid."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        df_raw = synthetic_time_series[["TowarId", "Year", "Week", "Quantity"]].copy()
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        predictions = forecaster.train_predict(df_filled, weeks_ahead=4, model_type=model_type)

        assert not predictions.empty, f"{model_name} should produce predictions"
        assert (predictions["Predicted_Qty"] >= 0).all(), f"{model_name} should have non-negative predictions"
        assert not predictions["Predicted_Qty"].isnull().any(), f"{model_name} should not have NaN predictions"


class TestModelAccuracy:
    """Test forecasting accuracy on known patterns."""

    def test_baseline_accuracy_on_stable_pattern(self):
        """Test baseline accuracy on constant pattern with small variation."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        np.random.seed(42)
        rows = []
        base_value = 100

        for week in range(52):
            date = pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=week)
            year = date.isocalendar()[0]
            week_num = date.isocalendar()[1]
            qty = base_value + np.random.normal(0, 2)

            rows.append({"TowarId": 1, "Year": year, "Week": week_num, "Quantity": qty})

        df_raw = pd.DataFrame(rows)
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        predictions = forecaster.predict_baseline(df_filled, weeks_ahead=4)

        avg_pred = predictions["Predicted_Qty"].mean()
        error_pct = abs(avg_pred - base_value) / base_value * 100

        assert error_pct < 5, f"Baseline error should be < 5%, got {error_pct:.2f}%"

    @pytest.mark.slow
    def test_rf_accuracy_on_stable_pattern(self):
        """Test Random Forest accuracy on stable pattern."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        np.random.seed(42)
        rows = []
        base_value = 100

        for week in range(52):
            date = pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=week)
            year = date.isocalendar()[0]
            week_num = date.isocalendar()[1]
            qty = base_value + np.random.normal(0, 2)

            rows.append({"TowarId": 1, "Year": year, "Week": week_num, "Quantity": qty})

        df_raw = pd.DataFrame(rows)
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()
        predictions = forecaster.train_predict(df_filled, weeks_ahead=4, model_type="rf")

        if not predictions.empty:
            avg_pred = predictions["Predicted_Qty"].mean()
            error_pct = abs(avg_pred - base_value) / base_value * 100

            assert error_pct < 15, f"RF error should be < 15%, got {error_pct:.2f}%"


class TestPredictionViewModel:
    """Test PredictionViewModel functionality."""

    def test_viewmodel_initialization(self, synthetic_time_series):
        """Test ViewModel can be initialized with mock data."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series
        from src.viewmodels.prediction_viewmodel import PredictionViewModel

        class MockDB:
            def __init__(self, test_df):
                self._test_df = test_df

            def get_historical_data(self):
                df = self._test_df.copy()
                df["Year"] = df["Date"].dt.isocalendar().year
                df["Week"] = df["Date"].dt.isocalendar().week
                return df[["TowarId", "Year", "Week", "Quantity"]]

        mock_db = MockDB(synthetic_time_series)
        forecaster = Forecaster()

        vm = PredictionViewModel(
            db=mock_db,
            forecaster=forecaster,
            prepare_time_series=prepare_time_series,
            fill_missing_weeks=fill_missing_weeks,
        )

        assert vm is not None

    def test_viewmodel_load_data(self, synthetic_time_series):
        """Test ViewModel data loading."""
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series
        from src.viewmodels.prediction_viewmodel import PredictionViewModel

        class MockDB:
            def __init__(self, test_df):
                self._test_df = test_df

            def get_historical_data(self):
                df = self._test_df.copy()
                df["Year"] = df["Date"].dt.isocalendar().year
                df["Week"] = df["Date"].dt.isocalendar().week
                return df[["TowarId", "Year", "Week", "Quantity"]]

        mock_db = MockDB(synthetic_time_series)
        forecaster = Forecaster()

        vm = PredictionViewModel(
            db=mock_db,
            forecaster=forecaster,
            prepare_time_series=prepare_time_series,
            fill_missing_weeks=fill_missing_weeks,
        )

        success = vm.load_data(force_refresh=True)

        assert success
        assert len(vm.prediction_state.available_products) > 0


class TestAnalysisViewModel:
    """Test AnalysisViewModel functionality."""

    def test_viewmodel_initialization(self, synthetic_time_series):
        """Test AnalysisViewModel can be initialized."""
        from src.preprocessing import fill_missing_weeks, prepare_time_series
        from src.viewmodels.analysis_viewmodel import AnalysisViewModel

        class MockDB:
            def __init__(self, test_df):
                self._test_df = test_df

            def get_current_stock(self):
                products = self._test_df["TowarId"].unique()
                return pd.DataFrame(
                    {
                        "TowarId": products,
                        "KodKreskowy": [f"CODE{p}" for p in products],
                        "Nazwa": [f"Product {p}" for p in products],
                        "Quantity": [100 + p * 10 for p in products],
                    }
                )

            def get_historical_data(self):
                df = self._test_df.copy()
                df["Year"] = df["Date"].dt.isocalendar().year
                df["Week"] = df["Date"].dt.isocalendar().week
                return df[["TowarId", "Year", "Week", "Quantity"]]

        mock_db = MockDB(synthetic_time_series)

        vm = AnalysisViewModel(
            db=mock_db, prepare_time_series=prepare_time_series, fill_missing_weeks=fill_missing_weeks
        )

        assert vm is not None

    def test_viewmodel_load_all_data(self, synthetic_time_series):
        """Test AnalysisViewModel loads all data correctly."""
        from src.preprocessing import fill_missing_weeks, prepare_time_series
        from src.viewmodels.analysis_viewmodel import AnalysisViewModel

        class MockDB:
            def __init__(self, test_df):
                self._test_df = test_df

            def get_current_stock(self):
                products = self._test_df["TowarId"].unique()
                return pd.DataFrame(
                    {
                        "TowarId": products,
                        "KodKreskowy": [f"CODE{p}" for p in products],
                        "Nazwa": [f"Product {p}" for p in products],
                        "Quantity": [100 + p * 10 for p in products],
                    }
                )

            def get_historical_data(self):
                df = self._test_df.copy()
                df["Year"] = df["Date"].dt.isocalendar().year
                df["Week"] = df["Date"].dt.isocalendar().week
                return df[["TowarId", "Year", "Week", "Quantity"]]

        mock_db = MockDB(synthetic_time_series)

        vm = AnalysisViewModel(
            db=mock_db, prepare_time_series=prepare_time_series, fill_missing_weeks=fill_missing_weeks
        )

        success = vm.load_all_data(force_refresh=True)

        assert success
        assert vm.analysis_state.df_stock is not None
