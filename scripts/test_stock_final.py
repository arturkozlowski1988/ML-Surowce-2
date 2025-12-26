import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_connector import DatabaseConnector

def test_final():
    print("Initializing DB...")
    db = DatabaseConnector()
    print("Debug: Inspecting columns for Towary and Zlecenia...")
    try:
        with db.engine.connect() as conn:
            from sqlalchemy import text
            # Check Towary Type
            try:
                # Check if Twr_Typ exists
                q1 = text("SELECT DISTINCT Twr_Typ FROM CDN.Towary")
                df1 = pd.read_sql(q1, conn)
                print(f"Distinct Twr_Typ values: {df1['Twr_Typ'].tolist()}")
            except Exception as e:
                print(f"Twr_Typ check failed (maybe column doesn't exist): {e}")
                # Try to list columns starting with Twr_
                q1b = text("SELECT TOP 1 * FROM CDN.Towary")
                df1b = pd.read_sql(q1b, conn)
                cols = [c for c in df1b.columns if c.startswith('Twr_T')]
                print(f"Columns starting with Twr_T: {cols}")

            # Check CZN columns
            try:
                q2 = text("SELECT TOP 1 * FROM dbo.CtiZlecenieNag")
                df2 = pd.read_sql(q2, conn)
                cols = [c for c in df2.columns if c.startswith('CZN_')]
                print(f"Columns starting with CZN_: {cols}")
            except Exception as e:
                print(f"CtiZlecenieNag check failed: {e}")
                
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    test_final()
