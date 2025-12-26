import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_connector import DatabaseConnector
from src.preprocessing import prepare_time_series, fill_missing_weeks

def debug_types():
    print("Connecting...")
    db = DatabaseConnector()
    
    print("Fetching History...")
    df_hist = db.get_historical_data()
    print("History Dtypes:")
    print(df_hist.dtypes)
    print(df_hist.head())
    
    print("\nFetching Stock...")
    df_stock = db.get_current_stock()
    print("Stock Dtypes:")
    print(df_stock.dtypes)
    print(df_stock.head())
    
    if not df_hist.empty and not df_stock.empty:
        # Check intersection
        hist_ids = df_hist['TowarId'].unique()
        stock_ids = df_stock['TowarId'].unique()
        
        print(f"\nExample History ID: {hist_ids[0]} (Type: {type(hist_ids[0])})")
        print(f"Example Stock ID: {stock_ids[0]} (Type: {type(stock_ids[0])})")
        
        # Check mapping logic
        df_stock['DisplayName'] = df_stock['Name'] + " (" + df_stock['Code'] + ")"
        product_map = dict(zip(df_stock['TowarId'], df_stock['DisplayName']))
        
        test_id = hist_ids[0]
        mapped = product_map.get(test_id, "NOT FOUND")
        print(f"Mapping check for {test_id}: {mapped}")
        
    # Check GenAI flow
    print("\nSimulating GenAI Flow...")
    if not df_hist.empty:
        df_clean = prepare_time_series(df_hist)
        print("Clean Dtypes:")
        print(df_clean.dtypes)
        
        try:
            target_id = df_stock['TowarId'].iloc[0]
            print(f"Filtering for {target_id}...")
            # This is where the error likely happens if column missing or type mismatch
            df_prod = df_clean[df_clean['TowarId'] == target_id]
            print(f"Filtered Rows: {len(df_prod)}")
        except Exception as e:
            print(f"GenAI Logic Error: {e}")

if __name__ == "__main__":
    debug_types()
