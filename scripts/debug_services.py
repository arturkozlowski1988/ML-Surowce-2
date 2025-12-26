import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_connector import DatabaseConnector
import pandas as pd

def debug_services():
    print("--- Debugging Services in Production Data ---")
    db = DatabaseConnector()
    
    # Check if there are items in CtiZlecenieElem with CZE_Typ IN (1, 2) that are ALSO Services (Twr_Typ = 2) in CDN.Towary
    query = """
    SELECT DISTINCT 
        t.Twr_Kod, 
        t.Twr_Nazwa, 
        t.Twr_Typ as CDN_Type, 
        e.CZE_Typ as CTI_Type
    FROM dbo.CtiZlecenieElem e
    JOIN CDN.Towary t ON e.CZE_TwrId = t.Twr_TwrId
    WHERE e.CZE_Typ IN (1, 2)
      AND t.Twr_Typ = 2 -- 2 usually means Service in CDN
    """
    
    print("Executing query to find Services masquerading as Raw Materials...")
    df = db.execute_query(query)
    
    if not df.empty:
        print(f"FOUND {len(df)} offending items!")
        print(df)
    else:
        print("No services found in the strict filtered set. Logic seems consistent.")

    # Also check specifically for "USŁUGA TRANSPORTOWA" if possible (by name pattern)
    query_specific = """
    SELECT DISTINCT 
        t.Twr_Kod, 
        t.Twr_Nazwa, 
        t.Twr_Typ as CDN_Type, 
        e.CZE_Typ as CTI_Type
    FROM dbo.CtiZlecenieElem e
    JOIN CDN.Towary t ON e.CZE_TwrId = t.Twr_TwrId
    WHERE e.CZE_Typ IN (1, 2)
      AND t.Twr_Nazwa LIKE '%TRANSPORT%'
    """
    print("\nChecking for 'TRANSPORT' items...")
    df_trans = db.execute_query(query_specific)
    print(df_trans)

if __name__ == "__main__":
    debug_services()
