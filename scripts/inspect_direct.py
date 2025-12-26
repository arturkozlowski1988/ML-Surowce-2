import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_connector import DatabaseConnector
from sqlalchemy import text

def inspect_direct_log():
    log_file = "schema_stock.log"
    target_tables = ['TwrZasoby', 'TwZasob', 'Towary']
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("Starting Stock Inspection...\n")
        try:
            db = DatabaseConnector()
            with db.engine.connect() as conn:
                for tbl in target_tables:
                    f.write(f"\n--- COLUMNS FOR dbo.{tbl} ---\n")
                    try:
                        q_cols = text(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tbl}'")
                        cols = conn.execute(q_cols)
                        col_names = [row[0] for row in cols]
                        f.write(f"{col_names}\n")
                    except Exception as e:
                        f.write(f"Error: {e}\n")

        except Exception as e:
            f.write(f"Fatal Error: {e}\n")

if __name__ == "__main__":
    inspect_direct_log()
