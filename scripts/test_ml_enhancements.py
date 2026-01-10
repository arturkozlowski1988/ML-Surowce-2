"""
ML Enhancements Test Suite

Tests for new ML features:
- Model persistence (save/load)
- Hyperparameter configuration
- MAPE/RMSE/MAE metrics
- LSTM forecasting (if TensorFlow available)
- Cross-validation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

# Test Results Tracker
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details = []
    
    def add_pass(self, name: str, info: str = ""):
        self.passed += 1
        self.details.append(f"✅ PASS: {name}" + (f" - {info}" if info else ""))
        print(self.details[-1])
    
    def add_fail(self, name: str, error: str):
        self.failed += 1
        self.details.append(f"❌ FAIL: {name} - {error}")
        print(self.details[-1])
    
    def add_skip(self, name: str, reason: str):
        self.skipped += 1
        self.details.append(f"⏭️ SKIP: {name} - {reason}")
        print(self.details[-1])
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {self.passed}/{total} passed, {self.failed} failed, {self.skipped} skipped")
        print("="*60)
        return self.failed == 0


def generate_test_data(n_weeks: int = 52) -> pd.DataFrame:
    """Generate synthetic time series data for testing."""
    np.random.seed(42)
    rows = []
    base_date = datetime(2024, 1, 1)
    
    for week in range(n_weeks):
        date = pd.Timestamp(base_date) + pd.Timedelta(weeks=week)
        year = date.isocalendar()[0]
        week_num = date.isocalendar()[1]
        
        # Pattern with trend and seasonality
        base = 100
        trend = 0.5 * week
        seasonal = 15 * np.sin(2 * np.pi * week / 13)
        noise = np.random.normal(0, 5)
        qty = max(0, base + trend + seasonal + noise)
        
        rows.append({
            'TowarId': 1,
            'Year': year,
            'Week': week_num,
            'Date': date,
            'Quantity': qty
        })
    
    return pd.DataFrame(rows)


def test_ml_config(results: TestResults):
    """Test ML configuration module."""
    print("\n" + "-"*40)
    print("TESTING: ML Configuration")
    print("-"*40)
    
    try:
        from src.ml_config import (
            MLConfig, load_config, save_config, 
            get_model_config, reset_to_defaults
        )
        
        # Test default config creation
        config = MLConfig()
        
        assert config.random_forest.n_estimators == 100, "RF n_estimators default wrong"
        assert config.gradient_boosting.learning_rate == 0.1, "GB learning_rate default wrong"
        assert config.lstm.units == 64, "LSTM units default wrong"
        
        results.add_pass("MLConfig defaults", "All default values correct")
        
        # Test config serialization
        config_dict = config.to_dict()
        assert 'random_forest' in config_dict
        assert 'gradient_boosting' in config_dict
        assert 'lstm' in config_dict
        
        results.add_pass("MLConfig serialization", "to_dict() works")
        
        # Test config deserialization
        config2 = MLConfig.from_dict(config_dict)
        assert config2.random_forest.n_estimators == config.random_forest.n_estimators
        
        results.add_pass("MLConfig deserialization", "from_dict() works")
        
        # Test get_model_config
        rf_params = get_model_config('rf', config)
        assert 'n_estimators' in rf_params
        assert rf_params['n_estimators'] == 100
        
        gb_params = get_model_config('gb', config)
        assert 'learning_rate' in gb_params
        
        lstm_params = get_model_config('lstm', config)
        assert 'units' in lstm_params
        
        results.add_pass("get_model_config", "Returns correct params for all models")
        
        # Test save/load with temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "test_ml_config.json"
            
            # Modify config
            config.random_forest.n_estimators = 200
            config.lstm.epochs = 100
            
            # Save
            success = save_config(config, temp_path)
            assert success, "save_config failed"
            assert temp_path.exists(), "Config file not created"
            
            results.add_pass("save_config", f"Saved to {temp_path}")
            
            # Load
            loaded_config = load_config(temp_path)
            assert loaded_config.random_forest.n_estimators == 200, "Loaded RF config wrong"
            assert loaded_config.lstm.epochs == 100, "Loaded LSTM config wrong"
            
            results.add_pass("load_config", "Loaded saved config correctly")
        
    except Exception as e:
        import traceback
        results.add_fail("ML Configuration", f"{e}\n{traceback.format_exc()}")


def test_model_manager(results: TestResults):
    """Test model persistence functionality."""
    print("\n" + "-"*40)
    print("TESTING: Model Manager (Persistence)")
    print("-"*40)
    
    try:
        from src.models.model_manager import ModelManager, ModelMetadata, SavedModelInfo
        from sklearn.ensemble import RandomForestRegressor
        
        # Create temp directory for models
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=Path(tmpdir))
            
            # Test directory creation
            assert Path(tmpdir).exists()
            results.add_pass("ModelManager init", "Directory created")
            
            # Create a simple model
            X = np.random.randn(100, 5)
            y = np.random.randn(100)
            model = RandomForestRegressor(n_estimators=10, random_state=42)
            model.fit(X, y)
            
            # Test save
            model_path = manager.save_model(
                model=model,
                model_type='rf',
                product_id=123,
                product_name='Test Product',
                training_time_ms=150.5,
                metrics={'mae': 1.5, 'rmse': 2.0, 'mape': 10.5},
                hyperparameters={'n_estimators': 10},
                data_info={'rows': 100, 'features': 5}
            )
            
            assert Path(model_path).exists(), "Model file not created"
            results.add_pass("save_model", f"Saved to {Path(model_path).name}")
            
            # Test metadata file exists
            metadata_path = Path(model_path).parent / f"{Path(model_path).stem}_metadata.json"
            assert metadata_path.exists(), "Metadata file not created"
            results.add_pass("save_model metadata", "Metadata JSON created")
            
            # Test load
            loaded_model, metadata = manager.load_model(model_path)
            
            assert loaded_model is not None
            assert metadata.product_id == 123
            assert metadata.model_type == 'rf'
            assert metadata.metrics['mae'] == 1.5
            
            results.add_pass("load_model", f"Loaded with metadata: product_id={metadata.product_id}")
            
            # Test prediction with loaded model
            test_pred = loaded_model.predict(X[:5])
            assert len(test_pred) == 5
            results.add_pass("loaded model prediction", "Model still works after load")
            
            # Test list_saved_models
            models = manager.list_saved_models()
            assert len(models) == 1
            assert models[0].product_id == 123
            
            results.add_pass("list_saved_models", f"Found {len(models)} model(s)")
            
            # Test delete
            deleted = manager.delete_model(model_path)
            assert deleted
            assert not Path(model_path).exists()
            
            results.add_pass("delete_model", "Model deleted successfully")
            
    except Exception as e:
        import traceback
        results.add_fail("Model Manager", f"{e}\n{traceback.format_exc()}")


def test_forecaster_metrics(results: TestResults):
    """Test MAPE/RMSE/MAE metrics calculation."""
    print("\n" + "-"*40)
    print("TESTING: Forecaster Metrics (MAPE/RMSE/MAE/R²)")
    print("-"*40)
    
    try:
        from src.forecasting import Forecaster, mean_absolute_percentage_error
        
        forecaster = Forecaster()
        
        # Test MAPE function
        y_true = np.array([100, 200, 150, 80])
        y_pred = np.array([110, 190, 160, 75])
        
        mape = mean_absolute_percentage_error(y_true, y_pred)
        assert 5 < mape < 10, f"MAPE should be ~7%, got {mape:.2f}%"
        
        results.add_pass("MAPE calculation", f"MAPE = {mape:.2f}%")
        
        # Test evaluate_model method
        metrics = forecaster.evaluate_model(y_true, y_pred)
        
        assert 'mape' in metrics, "Missing MAPE in metrics"
        assert 'rmse' in metrics, "Missing RMSE in metrics"
        assert 'mae' in metrics, "Missing MAE in metrics"
        assert 'r2' in metrics, "Missing R² in metrics"
        
        results.add_pass("evaluate_model", 
                        f"MAPE={metrics['mape']:.1f}%, RMSE={metrics['rmse']:.2f}, "
                        f"MAE={metrics['mae']:.2f}, R²={metrics['r2']:.3f}")
        
        # Test with perfect predictions
        y_perfect = y_true.copy()
        perfect_metrics = forecaster.evaluate_model(y_true, y_perfect)
        
        assert perfect_metrics['mape'] < 0.001, "Perfect MAPE should be ~0"
        assert perfect_metrics['rmse'] < 0.001, "Perfect RMSE should be ~0"
        assert perfect_metrics['mae'] < 0.001, "Perfect MAE should be ~0"
        assert perfect_metrics['r2'] > 0.999, "Perfect R² should be ~1"
        
        results.add_pass("Perfect prediction metrics", "All metrics validate perfect predictions")
        
    except Exception as e:
        import traceback
        results.add_fail("Forecaster Metrics", f"{e}\n{traceback.format_exc()}")


def test_forecaster_with_config(results: TestResults):
    """Test Forecaster using ML config."""
    print("\n" + "-"*40)
    print("TESTING: Forecaster with ML Config")
    print("-"*40)
    
    try:
        from src.forecasting import Forecaster
        from src.ml_config import MLConfig
        from src.preprocessing import prepare_time_series, fill_missing_weeks
        
        # Generate test data
        df = generate_test_data(n_weeks=52)
        
        # Create custom config
        config = MLConfig()
        config.random_forest.n_estimators = 50  # Faster for testing
        config.gradient_boosting.n_estimators = 50
        
        # Test Forecaster with custom config
        forecaster = Forecaster(config=config.to_dict())
        
        # Get model params
        rf_params = forecaster._get_model_params('rf')
        assert rf_params.get('n_estimators') == 50, f"Expected 50, got {rf_params.get('n_estimators')}"
        
        results.add_pass("Forecaster config loading", "Custom config applied")
        
        # Test prediction with config
        predictions = forecaster.train_predict(df, weeks_ahead=4, model_type='rf')
        
        assert not predictions.empty, "No predictions generated"
        assert len(predictions) == 4, f"Expected 4 predictions, got {len(predictions)}"
        
        results.add_pass("train_predict with config", f"{len(predictions)} predictions generated")
        
    except Exception as e:
        import traceback
        results.add_fail("Forecaster with Config", f"{e}\n{traceback.format_exc()}")


def test_lstm_forecaster(results: TestResults):
    """Test LSTM forecasting model."""
    print("\n" + "-"*40)
    print("TESTING: LSTM Forecaster")
    print("-"*40)
    
    # Check if TensorFlow is available
    from src.forecasting import Forecaster
    
    if not Forecaster.is_lstm_available():
        results.add_skip("LSTM Forecaster", "TensorFlow not installed")
        return
    
    try:
        from src.ml_config import MLConfig
        
        # Generate test data
        df = generate_test_data(n_weeks=52)
        
        # Create config with fast LSTM settings for testing
        config = MLConfig()
        config.lstm.epochs = 5  # Very fast for testing
        config.lstm.units = 16
        config.lstm.units_second = 8
        config.lstm.lookback = 4
        
        forecaster = Forecaster(config=config.to_dict())
        
        # Test LSTM prediction
        predictions = forecaster.train_predict(df, weeks_ahead=4, model_type='lstm')
        
        if predictions.empty:
            results.add_fail("LSTM Forecaster", "No predictions generated")
            return
        
        assert len(predictions) == 4, f"Expected 4 predictions, got {len(predictions)}"
        assert all(predictions['Predicted_Qty'] >= 0), "Negative predictions found"
        assert predictions['Model'].iloc[0] == 'LSTM (Deep Learning)'
        
        results.add_pass("LSTM Forecaster", f"{len(predictions)} predictions, avg={predictions['Predicted_Qty'].mean():.2f}")
        
        # Test get_last_model
        model = forecaster.get_last_model()
        results.add_pass("LSTM get_last_model", f"Model type: {type(model).__name__}")
        
    except Exception as e:
        import traceback
        results.add_fail("LSTM Forecaster", f"{e}\n{traceback.format_exc()}")


def test_cross_validation(results: TestResults):
    """Test cross-validation functionality."""
    print("\n" + "-"*40)
    print("TESTING: Cross-Validation")
    print("-"*40)
    
    try:
        from src.forecasting import Forecaster
        
        # Generate test data
        df = generate_test_data(n_weeks=52)
        
        forecaster = Forecaster()
        
        # Test cross-validation
        cv_metrics = forecaster.cross_validate(
            df, 
            product_id=1,
            model_type='rf',
            n_folds=3,
            test_size=4
        )
        
        if not cv_metrics:
            results.add_fail("Cross-validation", "No CV metrics returned")
            return
        
        assert 'mape' in cv_metrics, "Missing MAPE in CV metrics"
        assert 'mape_std' in cv_metrics, "Missing MAPE_std in CV metrics"
        assert 'rmse' in cv_metrics, "Missing RMSE in CV metrics"
        
        results.add_pass("Cross-validation", 
                        f"MAPE={cv_metrics['mape']:.2f}% (±{cv_metrics['mape_std']:.2f}), "
                        f"RMSE={cv_metrics['rmse']:.2f}")
        
    except Exception as e:
        import traceback
        results.add_fail("Cross-Validation", f"{e}\n{traceback.format_exc()}")


def test_model_type_enum(results: TestResults):
    """Test ModelType enum includes LSTM."""
    print("\n" + "-"*40)
    print("TESTING: ModelType Enum")
    print("-"*40)
    
    try:
        from src.viewmodels.prediction_viewmodel import ModelType
        
        # Check all model types
        expected_types = ['BASELINE', 'RANDOM_FOREST', 'GRADIENT_BOOSTING', 'EXPONENTIAL_SMOOTHING', 'LSTM']
        
        for model_type in expected_types:
            assert hasattr(ModelType, model_type), f"Missing {model_type} in ModelType enum"
        
        # Check LSTM value
        assert ModelType.LSTM.value == 'lstm', f"LSTM value should be 'lstm', got {ModelType.LSTM.value}"
        
        results.add_pass("ModelType Enum", f"Contains all {len(expected_types)} model types including LSTM")
        
    except Exception as e:
        results.add_fail("ModelType Enum", str(e))


def main():
    """Run all ML enhancement tests."""
    print("="*60)
    print("ML ENHANCEMENTS TEST SUITE")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}")
    
    results = TestResults()
    
    # 1. Test ML Configuration
    test_ml_config(results)
    
    # 2. Test Model Manager
    test_model_manager(results)
    
    # 3. Test Forecaster Metrics
    test_forecaster_metrics(results)
    
    # 4. Test Forecaster with Config
    test_forecaster_with_config(results)
    
    # 5. Test Cross-Validation
    test_cross_validation(results)
    
    # 6. Test ModelType Enum
    test_model_type_enum(results)
    
    # 7. Test LSTM (if available)
    test_lstm_forecaster(results)
    
    # Summary
    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
