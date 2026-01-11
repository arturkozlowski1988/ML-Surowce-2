"""
Comprehensive ML Pipeline Test Suite
Tests the forecasting system, ViewModels, and data preprocessing.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import numpy as np
import pandas as pd


# Test Results Tracker
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.details = []

    def add_pass(self, name: str, info: str = ""):
        self.passed += 1
        self.details.append(f"✅ PASS: {name}" + (f" - {info}" if info else ""))
        print(self.details[-1])

    def add_fail(self, name: str, error: str):
        self.failed += 1
        self.details.append(f"❌ FAIL: {name} - {error}")
        print(self.details[-1])

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {self.passed}/{total} passed, {self.failed} failed")
        print("=" * 60)
        return self.failed == 0


def generate_synthetic_data(n_weeks: int = 52, n_products: int = 3) -> pd.DataFrame:
    """Generate synthetic time series data for testing."""
    np.random.seed(42)
    rows = []

    base_date = datetime(2024, 1, 1)

    for pid in range(1, n_products + 1):
        # Base demand with trend and seasonality
        base_demand = 50 + pid * 20  # Different base per product
        trend = 0.5  # Slight upward trend

        for week in range(n_weeks):
            # Seasonal component (quarterly)
            seasonal = 15 * np.sin(2 * np.pi * week / 13)
            # Random noise
            noise = np.random.normal(0, 5)
            # Compute quantity
            qty = max(0, base_demand + trend * week + seasonal + noise)

            # Calculate year and week
            date = pd.Timestamp(base_date) + pd.Timedelta(weeks=week)
            year = date.isocalendar()[0]
            week_num = date.isocalendar()[1]

            rows.append({"TowarId": pid, "Year": year, "Week": week_num, "Quantity": round(qty, 2)})

    return pd.DataFrame(rows)


def test_preprocessing(results: TestResults) -> pd.DataFrame:
    """Test preprocessing functions."""
    print("\n" + "-" * 40)
    print("TESTING: Preprocessing Module")
    print("-" * 40)

    try:
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        # Generate test data
        df_raw = generate_synthetic_data(n_weeks=20, n_products=2)

        # Test prepare_time_series
        df_ts = prepare_time_series(df_raw.copy())

        if "Date" not in df_ts.columns:
            results.add_fail("prepare_time_series", "Date column not created")
            return None

        if df_ts["Date"].isnull().any():
            results.add_fail("prepare_time_series", "Date column has NaN values")
            return None

        results.add_pass("prepare_time_series", f"Created Date column for {len(df_ts)} rows")

        # Test fill_missing_weeks
        df_filled = fill_missing_weeks(df_ts.copy())

        n_products = df_raw["TowarId"].nunique()
        expected_min = len(df_raw)  # At least as many rows as original

        if len(df_filled) < expected_min:
            results.add_fail("fill_missing_weeks", f"Expected >= {expected_min} rows, got {len(df_filled)}")
            return None

        results.add_pass("fill_missing_weeks", f"Filled to {len(df_filled)} rows")

        return df_filled

    except Exception as e:
        results.add_fail("Preprocessing Import", str(e))
        return None


def test_forecaster_baseline(results: TestResults, df: pd.DataFrame) -> bool:
    """Test baseline forecasting model."""
    print("\n" + "-" * 40)
    print("TESTING: Forecaster - Baseline Model")
    print("-" * 40)

    try:
        from src.forecasting import Forecaster

        forecaster = Forecaster()

        # Test baseline prediction
        predictions = forecaster.predict_baseline(df, weeks_ahead=4)

        if predictions.empty:
            results.add_fail("Baseline Prediction", "No predictions generated")
            return False

        # Check expected columns
        expected_cols = {"TowarId", "Date", "Predicted_Qty", "Model"}
        if not expected_cols.issubset(predictions.columns):
            missing = expected_cols - set(predictions.columns)
            results.add_fail("Baseline Prediction", f"Missing columns: {missing}")
            return False

        # Validate prediction values
        n_products = df["TowarId"].nunique()
        expected_preds = n_products * 4  # 4 weeks ahead per product

        if len(predictions) != expected_preds:
            results.add_fail("Baseline Prediction", f"Expected {expected_preds} predictions, got {len(predictions)}")
            return False

        # Check no negative predictions
        if (predictions["Predicted_Qty"] < 0).any():
            results.add_fail("Baseline Prediction", "Negative predictions found")
            return False

        results.add_pass("Baseline Prediction", f"Generated {len(predictions)} valid predictions")
        return True

    except Exception as e:
        results.add_fail("Baseline Prediction", str(e))
        return False


def test_forecaster_ml_models(results: TestResults, df: pd.DataFrame) -> dict[str, bool]:
    """Test ML forecasting models (RF, GB, ES)."""
    print("\n" + "-" * 40)
    print("TESTING: Forecaster - ML Models")
    print("-" * 40)

    model_results = {}

    try:
        from src.forecasting import Forecaster

        forecaster = Forecaster()

        models_to_test = [("rf", "Random Forest"), ("gb", "Gradient Boosting"), ("es", "Exponential Smoothing")]

        for model_type, model_name in models_to_test:
            try:
                predictions = forecaster.train_predict(df, weeks_ahead=4, model_type=model_type)

                if predictions.empty:
                    results.add_fail(f"{model_name} Model", "No predictions generated")
                    model_results[model_type] = False
                    continue

                # Validate predictions
                if (predictions["Predicted_Qty"] < 0).any():
                    results.add_fail(f"{model_name} Model", "Negative predictions found")
                    model_results[model_type] = False
                    continue

                # Check reasonable values (not NaN, not Inf)
                if predictions["Predicted_Qty"].isnull().any() or np.isinf(predictions["Predicted_Qty"]).any():
                    results.add_fail(f"{model_name} Model", "Invalid prediction values (NaN/Inf)")
                    model_results[model_type] = False
                    continue

                avg_pred = predictions["Predicted_Qty"].mean()
                results.add_pass(f"{model_name} Model", f"{len(predictions)} predictions, avg: {avg_pred:.2f}")
                model_results[model_type] = True

            except Exception as e:
                results.add_fail(f"{model_name} Model", str(e))
                model_results[model_type] = False

        return model_results

    except Exception as e:
        results.add_fail("ML Models Import", str(e))
        return {m[0]: False for m in [("rf", ""), ("gb", ""), ("es", "")]}


def test_prediction_viewmodel(results: TestResults, df: pd.DataFrame) -> bool:
    """Test PredictionViewModel functionality."""
    print("\n" + "-" * 40)
    print("TESTING: PredictionViewModel")
    print("-" * 40)

    try:
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series
        from src.viewmodels.prediction_viewmodel import ModelType, PredictionViewModel

        # Create mock database that returns our test data
        class MockDB:
            def __init__(self, test_df):
                self._test_df = test_df

            def get_weekly_usage_history(self):
                # Convert back to raw format
                df = self._test_df.copy()
                df["Year"] = df["Date"].dt.isocalendar().year
                df["Week"] = df["Date"].dt.isocalendar().week
                return df[["TowarId", "Year", "Week", "Quantity"]]

        mock_db = MockDB(df)
        forecaster = Forecaster()

        # Initialize ViewModel
        vm = PredictionViewModel(
            db=mock_db,
            forecaster=forecaster,
            prepare_time_series=prepare_time_series,
            fill_missing_weeks=fill_missing_weeks,
        )

        results.add_pass("ViewModel Initialization", "Created successfully")

        # Test data loading
        success = vm.load_data(force_refresh=True)

        if not success:
            results.add_fail("ViewModel load_data", "Failed to load data")
            return False

        results.add_pass("ViewModel load_data", f"Loaded {len(vm.prediction_state.available_products)} products")

        # Test model training
        if vm.prediction_state.available_products:
            product_id = vm.prediction_state.available_products[0]

            for model_type in [ModelType.BASELINE, ModelType.RANDOM_FOREST]:
                result = vm.train_model(product_id, model_type, weeks_ahead=4)

                if result is None or result.error:
                    results.add_fail(
                        f"ViewModel train_model ({model_type.value})", result.error if result else "No result returned"
                    )
                    return False

                if result.predictions.empty:
                    results.add_fail(f"ViewModel train_model ({model_type.value})", "Empty predictions")
                    return False

                results.add_pass(
                    f"ViewModel train_model ({model_type.value})",
                    f"{len(result.predictions)} predictions, time: {result.training_time_ms:.2f}ms",
                )

        # Test combined data for charting
        if vm.prediction_state.model_results:
            product_id = vm.prediction_state.available_products[0]
            combined_df = vm.get_combined_forecast_data(product_id, ModelType.RANDOM_FOREST)

            if combined_df is None or combined_df.empty:
                results.add_fail("ViewModel get_combined_forecast_data", "No data returned")
                return False

            # Check required columns for charting
            if "Type" not in combined_df.columns:
                results.add_fail("ViewModel get_combined_forecast_data", "Missing Type column")
                return False

            types = combined_df["Type"].unique()
            if "Historical" not in types or "Forecast" not in types:
                results.add_fail("ViewModel get_combined_forecast_data", f"Missing data types. Found: {types}")
                return False

            results.add_pass("ViewModel get_combined_forecast_data", f"{len(combined_df)} rows, types: {list(types)}")

        return True

    except Exception as e:
        import traceback

        results.add_fail("PredictionViewModel Test", f"{str(e)}\n{traceback.format_exc()}")
        return False


def test_analysis_viewmodel(results: TestResults, df: pd.DataFrame) -> bool:
    """Test AnalysisViewModel functionality."""
    print("\n" + "-" * 40)
    print("TESTING: AnalysisViewModel")
    print("-" * 40)

    try:
        from src.preprocessing import fill_missing_weeks, prepare_time_series
        from src.viewmodels.analysis_viewmodel import AnalysisViewModel

        # Create mock database
        class MockDB:
            def __init__(self, test_df):
                self._test_df = test_df

            def get_current_stock(self):
                # Mock stock data
                products = self._test_df["TowarId"].unique()
                return pd.DataFrame(
                    {
                        "TowarId": products,
                        "KodKreskowy": [f"CODE{p}" for p in products],
                        "Nazwa": [f"Product {p}" for p in products],
                        "Quantity": [100 + p * 10 for p in products],
                    }
                )

            def get_weekly_usage_history(self):
                df = self._test_df.copy()
                df["Year"] = df["Date"].dt.isocalendar().year
                df["Week"] = df["Date"].dt.isocalendar().week
                return df[["TowarId", "Year", "Week", "Quantity"]]

        mock_db = MockDB(df)

        # Initialize ViewModel
        vm = AnalysisViewModel(
            db=mock_db, prepare_time_series=prepare_time_series, fill_missing_weeks=fill_missing_weeks
        )

        results.add_pass("AnalysisViewModel Initialization", "Created successfully")

        # Test loading all data
        success = vm.load_all_data(force_refresh=True)

        if not success:
            results.add_fail("AnalysisViewModel load_all_data", "Failed to load data")
            return False

        results.add_pass(
            "AnalysisViewModel load_all_data",
            f"Stock: {len(vm.analysis_state.df_stock) if vm.analysis_state.df_stock is not None else 0} rows",
        )

        # Test summary calculation
        if vm.analysis_state.summary:
            summary = vm.analysis_state.summary
            results.add_pass(
                "AnalysisViewModel Summary",
                f"Total qty: {summary.total_quantity:.2f}, Products: {summary.total_products}",
            )
        else:
            results.add_fail("AnalysisViewModel Summary", "No summary calculated")
            return False

        # Test date filtering
        if vm.analysis_state.df_historical is not None and not vm.analysis_state.df_historical.empty:
            min_date = df["Date"].min()
            max_date = df["Date"].max()
            mid_date = min_date + (max_date - min_date) / 2

            vm.apply_date_filter(mid_date, max_date)

            if vm.analysis_state.df_filtered is not None:
                results.add_pass(
                    "AnalysisViewModel apply_date_filter", f"Filtered to {len(vm.analysis_state.df_filtered)} rows"
                )
            else:
                results.add_fail("AnalysisViewModel apply_date_filter", "No filtered data")
                return False

        return True

    except Exception as e:
        import traceback

        results.add_fail("AnalysisViewModel Test", f"{str(e)}\n{traceback.format_exc()}")
        return False


def test_model_accuracy(results: TestResults) -> bool:
    """Test forecasting accuracy on known patterns."""
    print("\n" + "-" * 40)
    print("TESTING: Model Accuracy on Known Pattern")
    print("-" * 40)

    try:
        from src.forecasting import Forecaster
        from src.preprocessing import fill_missing_weeks, prepare_time_series

        # Create data with known trend (constant + small variation)
        np.random.seed(42)
        rows = []
        base_value = 100

        for week in range(52):
            date = pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=week)
            year = date.isocalendar()[0]
            week_num = date.isocalendar()[1]

            # Known stable pattern
            qty = base_value + np.random.normal(0, 2)  # Very small variation

            rows.append({"TowarId": 1, "Year": year, "Week": week_num, "Quantity": qty})

        df_raw = pd.DataFrame(rows)
        df_ts = prepare_time_series(df_raw)
        df_filled = fill_missing_weeks(df_ts)

        forecaster = Forecaster()

        # For a stable pattern, predictions should be close to base_value
        predictions = forecaster.predict_baseline(df_filled, weeks_ahead=4)

        if predictions.empty:
            results.add_fail("Accuracy Test - Baseline", "No predictions")
            return False

        avg_pred = predictions["Predicted_Qty"].mean()
        error_pct = abs(avg_pred - base_value) / base_value * 100

        if error_pct > 5:  # Allow 5% error
            results.add_fail(
                "Accuracy Test - Baseline",
                f"High error: {error_pct:.2f}% (predicted {avg_pred:.2f} vs expected ~{base_value})",
            )
            return False

        results.add_pass(
            "Accuracy Test - Baseline", f"Error: {error_pct:.2f}% (predicted {avg_pred:.2f} vs base {base_value})"
        )

        # Test RF
        predictions_rf = forecaster.train_predict(df_filled, weeks_ahead=4, model_type="rf")

        if not predictions_rf.empty:
            avg_pred_rf = predictions_rf["Predicted_Qty"].mean()
            error_pct_rf = abs(avg_pred_rf - base_value) / base_value * 100

            if error_pct_rf < 15:  # More lenient for ML model
                results.add_pass(
                    "Accuracy Test - Random Forest", f"Error: {error_pct_rf:.2f}% (predicted {avg_pred_rf:.2f})"
                )
            else:
                results.add_fail("Accuracy Test - Random Forest", f"High error: {error_pct_rf:.2f}%")
                return False

        return True

    except Exception as e:
        results.add_fail("Accuracy Test", str(e))
        return False


def main():
    """Run all ML pipeline tests."""
    print("=" * 60)
    print("ML PIPELINE COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")

    results = TestResults()

    # 1. Test Preprocessing
    df = test_preprocessing(results)

    if df is None:
        print("\n⚠️ Preprocessing failed, skipping dependent tests")
    else:
        # 2. Test Baseline Forecaster
        test_forecaster_baseline(results, df)

        # 3. Test ML Models
        test_forecaster_ml_models(results, df)

        # 4. Test PredictionViewModel
        test_prediction_viewmodel(results, df)

        # 5. Test AnalysisViewModel
        test_analysis_viewmodel(results, df)

        # 6. Test Model Accuracy
        test_model_accuracy(results)

    # Summary
    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
