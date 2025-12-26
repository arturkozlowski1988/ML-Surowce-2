import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_connector import DatabaseConnector
import pandas as pd

def verify_new_features():
    print("--- Verifying Sorting and Full Product AI ---")
    db = DatabaseConnector()
    
    # 1. Verify Sorting (UsageCount)
    print("\n1. Fetching Stock (Sorted)...")
    df_stock = db.get_current_stock()
    if not df_stock.empty and 'UsageCount' in df_stock.columns:
        print("Success: UsageCount column found.")
        print("Top 5 Products by Usage:")
        print(df_stock[['Name', 'UsageCount']].head())
        # Check if actually sorted
        if df_stock['UsageCount'].is_monotonic_decreasing:
             print("SUCCESS: Data is correctly sorted by UsageCount DESC.")
        else:
             print("WARNING: Data might not be strictly sorted (check SQL).")
    else:
        print("FAILED: UsageCount missing or DF empty.")

    # 2. Verify Product List for AI
    print("\n2. Fetching Products with Technology...")
    df_tech = db.get_products_with_technology()
    if not df_tech.empty:
        print(f"Success. Found {len(df_tech)} products with defined technology.")
        print(df_tech.head(3))
        
        # 3. Verify AI Data (BOM + Stock)
        test_prod_id = df_tech['FinalProductId'].iloc[0]
        print(f"\n3. Fetching BOM with Stock for Product ID {test_prod_id}...")
        df_bom_ai = db.get_bom_with_stock(int(test_prod_id))
        
        if not df_bom_ai.empty:
            print(f"Success. BOM has {len(df_bom_ai)} ingredients.")
            print(df_bom_ai.head())
            if 'CurrentStock' in df_bom_ai.columns:
                print("SUCCESS: CurrentStock column present in BOM for AI.")
            else:
                print("FAILED: CurrentStock missing.")
        else:
             print("Warning: BOM empty for this product (might be filtered out).")
    else:
        print("Warning: No products with technology found.")

if __name__ == "__main__":
    verify_new_features()
