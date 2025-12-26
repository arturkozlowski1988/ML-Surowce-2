import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_connector import DatabaseConnector

def main():
    print("Testing Database Connection...")
    try:
        db = DatabaseConnector()
        if db.test_connection():
            print("SUCCESS: Connected to Database!")
            
            print("\nTesting: get_current_stock()...")
            df_stock = db.get_current_stock()
            print(f"Result: {len(df_stock)} rows")
            if not df_stock.empty:
                print(df_stock.head(2).to_string())
            else:
                print("Warning: Stock dataframe is empty.")

            print("\nTesting: get_historical_data()...")
            df_hist = db.get_historical_data()
            print(f"Result: {len(df_hist)} rows")
            if not df_hist.empty:
                print(df_hist.head(2).to_string())
            else:
                print("Warning: Historical dataframe is empty.")
                
        else:
            print("FAILURE: Connection test returned False.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
