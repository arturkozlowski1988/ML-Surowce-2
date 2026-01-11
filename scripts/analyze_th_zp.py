import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_connector import DatabaseConnector


def analyze_system():
    print("--- 1. Sanity Check: DatabaseConnector Methods ---")
    try:
        db = DatabaseConnector()
        if hasattr(db, "get_products_with_technology"):
            print("SUCCESS: 'get_products_with_technology' exists.")
        else:
            print("CRITICAL: 'get_products_with_technology' MISSING!")
            return
    except Exception as e:
        print(f"Error initializing DB: {e}")
        return

    print("\n--- 2. Production Order (ZP) vs Technology (TH) Analysis ---")
    # Goal: Find how ZP links to TH

    # 2.1 Inspect Columns of CtiZlecenieNag to find TH link
    print("Inspecting CtiZlecenieNag columns...")
    q_cols = "SELECT TOP 1 * FROM dbo.CtiZlecenieNag"
    df_zn = db.execute_query(q_cols)
    if not df_zn.empty:
        print("Columns in CtiZlecenieNag:", df_zn.columns.tolist())

    # 2.2 Inspect Columns of CtiTechnolNag
    print("\nInspecting CtiTechnolNag columns...")
    q_cols_th = "SELECT TOP 1 * FROM dbo.CtiTechnolNag"
    df_th = db.execute_query(q_cols_th)
    if not df_th.empty:
        print("Columns in CtiTechnolNag:", df_th.columns.tolist())

    # 2.3 Check for data consistency
    # Does ZP have a CTN_ID reference?
    # Usually CZN_CTNId or similar.
    potential_keys = [c for c in df_zn.columns if "CTN" in c]
    print(f"\nPotential FKs to Technology in ZP: {potential_keys}")

    if potential_keys:
        key = potential_keys[0]
        print(f"Checking link via {key}...")
        q_check = f"""
        SELECT TOP 5
            zp.CZN_ID, zp.CZN_Kod, zp.{key}, th.CTN_Kod, th.CTN_Nazwa
        FROM dbo.CtiZlecenieNag zp
        LEFT JOIN dbo.CtiTechnolNag th ON zp.{key} = th.CTN_ID
        WHERE zp.{key} IS NOT NULL
        """
        df_link = db.execute_query(q_check)
        print(df_link)
    else:
        print("No obvious column with 'CTN' in name found in CtiZlecenieNag.")
        # Try matching by Product ID (TwrId)
        print("Checking overlap by Product ID (TwrId)...")
        q_Twr = """
        SELECT TOP 5
            zp.CZN_ID, zp.CZN_Kod, zp.CZN_TwrId, th.CTN_ID
        FROM dbo.CtiZlecenieNag zp
        JOIN dbo.CtiTechnolNag th ON zp.CZN_TwrId = th.CTN_TwrId
        ORDER BY zp.CZN_ID DESC
        """
        df_twr_link = db.execute_query(q_Twr)
        print(df_twr_link)


if __name__ == "__main__":
    analyze_system()
