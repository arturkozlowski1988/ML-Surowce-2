import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_connector import DatabaseConnector
import pandas as pd

def check_technology_schema():
    print("--- Inspecting CtiTechnolNag & CtiTechnolElem ---")
    db = DatabaseConnector()
    
    tables = ["CtiTechnolNag", "CtiTechnolElem"]
    
    for tbl in tables:
        print(f"\nTABLE: {tbl}")
        try:
            # Get one row to see columns
            query = f"SELECT TOP 1 * FROM dbo.{tbl} WITH (NOLOCK)"
            df = db.execute_query(query)
            if not df.empty:
                print("Columns:")
                print(df.columns.tolist())
            else:
                # Fallback if empty, try to get from information schema
                print("Table empty, fetching columns from schema...")
                query_schema = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tbl}'"
                df_cols = db.execute_query(query_schema)
                print(df_cols['COLUMN_NAME'].tolist())
        except Exception as e:
            print(f"Error inspecting {tbl}: {e}")

if __name__ == "__main__":
    check_technology_schema()
