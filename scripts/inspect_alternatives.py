import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_connector import DatabaseConnector

def inspect_alternatives():
    db = DatabaseConnector()
    print("Checking CtiTowary...")
    try:
        with db.engine.connect() as conn:
            # Check CtiTowary
            try:
                q = text("SELECT TOP 1 * FROM dbo.CtiTowary")
                res = conn.execute(q).fetchall()
                print(f"dbo.CtiTowary exists! Rows: {len(res)}")
                print(f"Columns: {res[0].keys() if res else 'No rows'}")
            except Exception as e:
                print(f"dbo.CtiTowary failed: {e}")

            # Check CDN.Towary
            try:
                q = text("SELECT TOP 1 * FROM CDN.Towary")
                res = conn.execute(q).fetchall()
                print(f"CDN.Towary exists! Rows: {len(res)}")
            except Exception as e:
                print(f"CDN.Towary failed: {e}")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    inspect_alternatives()
