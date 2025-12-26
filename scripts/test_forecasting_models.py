import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.forecasting import Forecaster

def create_dummy_data():
    dates = pd.date_range(start='2024-01-01', periods=50, freq='W-SUN')
    
    # Product 1: Linear Trend
    data1 = []
    for i, d in enumerate(dates):
        qty = 100 + i * 2 + np.random.normal(0, 5) # Trend
        data1.append({'TowarId': 1, 'Date': d, 'Quantity': max(0, qty)})
        
    # Product 2: Seasonality
    data2 = []
    for i, d in enumerate(dates):
        qty = 100 + 50 * np.sin(i / 4) + np.random.normal(0, 5) # Seasonality
        data2.append({'TowarId': 2, 'Date': d, 'Quantity': max(0, qty)})
        
    return pd.DataFrame(data1 + data2)

def test_models():
    print("--- STARTING FORECASTING MODEL TESTS ---")
    df = create_dummy_data()
    print(f"Created dummy data: {len(df)} rows, {df['TowarId'].nunique()} products.")
    
    forecaster = Forecaster()
    
    models_to_test = ['rf', 'gb', 'es']
    
    for model_type in models_to_test:
        print(f"\nTesting model: {model_type}...")
        try:
            preds = forecaster.train_predict(df, weeks_ahead=4, model_type=model_type)
            
            if preds.empty:
                print(f"❌ FAIL: {model_type} returned empty predictions.")
            else:
                print(f"✅ SUCCESS: {model_type} returned {len(preds)} predictions.")
                print(preds.head(2))
                
                # Check for NaNs
                if preds['Predicted_Qty'].isnull().any():
                     print(f"❌ FAIL: {model_type} contains NaNs.")
                
                # Check distinct models column
                unique_models = preds['Model'].unique()
                print(f"   Model name in output: {unique_models}")
                
        except Exception as e:
            print(f"❌ ERROR: {model_type} crashed: {e}")
            import traceback
            traceback.print_exc()

    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    test_models()
