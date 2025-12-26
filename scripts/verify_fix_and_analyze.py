import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_connector import DatabaseConnector
import pandas as pd

def verify_and_analyze():
    print("--- 1. Verifying Fix: get_products_with_technology ---")
    db = DatabaseConnector()
    try:
        df = db.get_products_with_technology()
        print(f"SUCCESS: Method called. Returned {len(df)} products.")
        if not df.empty:
            print(df.head(2))
    except AttributeError:
        print("CRITICAL FAIL: Method still missing!")
    except Exception as e:
        print(f"Error calling method: {e}")

    print("\n--- 2. Analyzing Schema (ZP vs TH) ---")
    
    # query information schema for columns
    q_schema = """
    SELECT TABLE_NAME, COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME IN ('CtiZlecenieNag', 'CtiTechnolNag')
    ORDER BY TABLE_NAME, COLUMN_NAME
    """
    df_cols = db.execute_query(q_schema)
    
    if not df_cols.empty:
        zp_cols = df_cols[df_cols['TABLE_NAME'] == 'CtiZlecenieNag']['COLUMN_NAME'].tolist()
        th_cols = df_cols[df_cols['TABLE_NAME'] == 'CtiTechnolNag']['COLUMN_NAME'].tolist()
        
        print(f"ZP Columns: {zp_cols}")
        print(f"TH Columns: {th_cols}")
        
        # Check for overlaps / keys
        print("\n--- Relationship Hypothesis ---")
        ctn_in_zp = [c for c in zp_cols if 'CTN' in c] # Standard CTI prefix for TechnolNag ID is often CTN...
        if ctn_in_zp:
             print(f"Direct Link Found? ZP columns containing 'CTN': {ctn_in_zp}")
        
        czn_in_th = [c for c in th_cols if 'CZN' in c]
        if czn_in_th:
             print(f"Reverse Link Found? TH columns containing 'CZN': {czn_in_th}")

        print(f"Common 'TwrId' columns? {'CZE_TwrId' in zp_cols or 'CZN_TwrId' in zp_cols}")

if __name__ == "__main__":
    verify_and_analyze()
