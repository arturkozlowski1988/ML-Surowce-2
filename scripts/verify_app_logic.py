import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

from src.ai_engine.ollama_client import OllamaClient
from src.db_connector import DatabaseConnector
from src.preprocessing import prepare_time_series


def mocked_app_logic():
    print("--- Starting App Logic Verification ---")
    db = DatabaseConnector()

    # 1. Fetch Global Data
    df_stock = db.get_current_stock()
    if df_stock.empty:
        print("CRITICAL: No stock data found.")
        return

    # Map IDs to Names
    df_stock["TowarId"] = pd.to_numeric(df_stock["TowarId"], errors="coerce").fillna(0).astype(int)
    product_map = dict(zip(df_stock["TowarId"], df_stock["Name"] + " (" + df_stock["Code"] + ")", strict=False))

    # 2. Fetch Historical Data
    df_hist = db.get_historical_data()
    if df_hist.empty:
        print("CRITICAL: No historical data found.")
        return

    df_clean = prepare_time_series(df_hist)
    df_clean["TowarId"] = pd.to_numeric(df_clean["TowarId"], errors="coerce").fillna(0).astype(int)

    # --- TEST CASE 1: Empty Product (Simulated) ---
    # We know some products likely have no history if they are in stock but not in production history
    all_stock_ids = set(df_stock["TowarId"].unique())
    all_hist_ids = set(df_clean["TowarId"].unique())

    empty_candidates = list(all_stock_ids - all_hist_ids)

    if empty_candidates:
        test_empty_id = empty_candidates[0]
        print(
            f"\n[TEST 1] Testing Empty Data Product: ID {test_empty_id} ({product_map.get(test_empty_id, 'Unknown')})"
        )

        df_prod_empty = df_clean[df_clean["TowarId"] == test_empty_id].copy()

        if df_prod_empty.empty:
            print("SUCCESS: Product df is empty as expected.")
            print("Action: App would show WARNING.")
        else:
            print("FAILURE: Product df is NOT empty?")
    else:
        print("[TEST 1] Skipped - All stock products have history?")

    # --- TEST CASE 2: Valid Product ---
    valid_candidates = list(all_hist_ids)
    if valid_candidates:
        test_valid_id = 2540  # From previous output if available, or just pick one
        if test_valid_id not in valid_candidates:
            test_valid_id = valid_candidates[0]

        print(
            f"\n[TEST 2] Testing Valid Data Product: ID {test_valid_id} ({product_map.get(test_valid_id, 'Unknown')})"
        )

        df_prod_valid = df_clean[df_clean["TowarId"] == test_valid_id].copy()

        if not df_prod_valid.empty:
            print(f"Data found: {len(df_prod_valid)} records.")

            # Prepare Prompt (replicating main.py logic)
            last_4_weeks = df_prod_valid["Quantity"].tail(4).tolist()
            avg_consumption = sum(last_4_weeks) / len(last_4_weeks) if last_4_weeks else 0
            product_name = product_map.get(test_valid_id, f"ID {test_valid_id}")

            prompt = f"Analyze {product_name}. Last 4 weeks: {last_4_weeks}. Avg: {avg_consumption:.2f}."
            print(f"Generated Prompt: {prompt}")

            # Call Ollama
            print("Calling Ollama (ministral-3:8b)...")
            try:
                client = OllamaClient(model_name="ministral-3:8b")
                response = client.generate_explanation(prompt)
                print("Ollama Response Received:")
                print(response[:100] + "...")
                print("SUCCESS: Logic verified.")
            except Exception as e:
                print(f"FAILURE: Ollama crashed: {e}")
        else:
            print("FAILURE: Selected valid product has no data during test extract?")

    print("\n--- Verification Complete ---")


if __name__ == "__main__":
    mocked_app_logic()
