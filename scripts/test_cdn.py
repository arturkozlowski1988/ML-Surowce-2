import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_connector import DatabaseConnector

def test_cdn():
    db = DatabaseConnector()
    try:
        with db.engine.connect() as conn:
            # Test 1: CDN.Towary + dbo.TwrZasoby
            print("Test 1: CDN.Towary + dbo.TwrZasoby")
            q1 = text("""
                SELECT TOP 5 t.Twr_Kod, t.Twr_Nazwa 
                FROM CDN.Towary t
                JOIN dbo.TwrZasoby z ON t.Twr_TwrId = z.TwZ_TwrId
            """)
            try:
                res = conn.execute(q1).fetchall()
                print(f"Success! Rows: {len(res)}")
                print(res)
            except Exception as e:
                print(f"Failed: {e}")

            # Test 2: CDN.Towary + CDN.TwrZasoby
            print("\nTest 2: CDN.Towary + CDN.TwrZasoby")
            q2 = text("""
                SELECT TOP 5 t.Twr_Kod, t.Twr_Nazwa 
                FROM CDN.Towary t
                JOIN CDN.TwrZasoby z ON t.Twr_TwrId = z.TwZ_TwrId
            """)
            try:
                res = conn.execute(q2).fetchall()
                print(f"Success! Rows: {len(res)}")
            except Exception as e:
                print(f"Failed: {e}")

    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    test_cdn()
