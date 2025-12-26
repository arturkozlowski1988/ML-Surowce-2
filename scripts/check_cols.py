import sys
import os
sys.path.append(os.getcwd())
from src.db_connector import DatabaseConnector
from sqlalchemy import text
import pandas as pd

def check():
    db = DatabaseConnector()
    with db.engine.connect() as conn:
        try:
            # Check Zlecenie
            df2 = pd.read_sql(text("SELECT TOP 1 * FROM dbo.CtiZlecenieNag"), conn)
            print("CtiZlecenieNag Columns:")
            print(list(df2.columns))
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check()
