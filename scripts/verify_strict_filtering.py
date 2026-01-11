import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_connector import DatabaseConnector


def verify_strict_filtering():
    print("--- Verifying Strict Filtering (CZE_Typ 1,2) ---")
    db = DatabaseConnector()

    # 1. Historical Data
    print("\n1. Fetching Historical Data...")
    try:
        df_hist = db.get_historical_data()
        if not df_hist.empty:
            print(f"Success. Fetched {len(df_hist)} records.")
            print(df_hist.head())
        else:
            print("Warning: No historical data found matching strict criteria.")
    except Exception as e:
        print(f"FAILED: {e}")

    # 2. Current Stock
    print("\n2. Fetching Current Stock (Restricted)...")
    try:
        df_stock = db.get_current_stock()
        if not df_stock.empty:
            print(f"Success. Fetched {len(df_stock)} products.")
            print(df_stock.head())
        else:
            print("Warning: No stock data found matching strict criteria.")
    except Exception as e:
        print(f"FAILED: {e}")

    # 3. Usage Stats (Specific ID - assuming we found one in hist)
    if not df_hist.empty:
        test_id = df_hist["TowarId"].iloc[0]
        print(f"\n3. Fetching Usage Stats for ID {test_id}...")
        try:
            df_usage = db.get_product_usage_stats(int(test_id))
            if not df_usage.empty:
                print(f"Success. Fetched {len(df_usage)} usage records.")
                print(df_usage.head())
            else:
                print("Info: No usage stats for this specific ID (might be old history).")
        except Exception as e:
            print(f"FAILED: {e}")


if __name__ == "__main__":
    verify_strict_filtering()
