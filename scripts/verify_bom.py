import io
import os
import sys

# Fix encoding for Windows console (CP1250 -> UTF-8)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_connector import DatabaseConnector


def verify_bom_flow():
    print("--- Verifying BOM Data Flow ---")
    db = DatabaseConnector()

    # 1. Get a Raw Material from History
    print("\n1. Finding a raw material with history...")
    df_hist = db.get_historical_data()
    if df_hist.empty:
        print("Error: No history data.")
        return

    test_raw_id = int(df_hist["TowarId"].iloc[0])
    print(f"   Selected Raw Material ID: {test_raw_id}")

    # 2. Get Usage Stats
    print(f"\n2. Fetching Usage Stats for RM {test_raw_id}...")
    df_usage = db.get_product_usage_stats(test_raw_id)

    if df_usage.empty:
        print("   No usage found for this RM. Trying another...")
        # Try to find one with usage
        for rid in df_hist["TowarId"].unique()[:5]:
            df_u = db.get_product_usage_stats(int(rid))
            if not df_u.empty:
                test_raw_id = int(rid)
                df_usage = df_u
                print(f"   Found RM with usage! ID: {test_raw_id}")
                break

    if df_usage.empty:
        print("Warning: Could not find any RM with active usage in top 5 items.")
        return

    print("   Usage Stats Columns:", df_usage.columns.tolist())
    if "FinalProductId" not in df_usage.columns:
        print("ERROR: FinalProductId missing from usage stats!")
        return

    # 3. Pick a Final Product and Get BOM
    final_prod_id = int(df_usage["FinalProductId"].iloc[0])
    final_prod_name = df_usage["FinalProductName"].iloc[0]
    print(f"\n3. Fetching BOM for Final Product: {final_prod_name} (ID: {final_prod_id})...")

    df_bom = db.get_product_bom(final_prod_id)

    if not df_bom.empty:
        print(f"   Success! BOM found with {len(df_bom)} ingredients.")
        print(df_bom[["IngredientCode", "QuantityPerUnit", "Type"]].head())
    else:
        print("   Warning: BOM is empty. (Product might not have active tech or strict filtering excluded all items).")


if __name__ == "__main__":
    verify_bom_flow()
