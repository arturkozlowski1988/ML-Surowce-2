import sys
import os
import pandas as pd
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db_connector import DatabaseConnector

def inspect_schema():
    output_file = "schema_info.txt"
    db = DatabaseConnector()
    # Common prefixes/variations to check if standard names fail
    tables = ['dbo.CtiZlecenieElem', 'dbo.CtiZlecenieNag', 'dbo.TwZasob', 'dbo.Towary']
    
    with open(output_file, "w", encoding="utf-8") as f:
        try:
            with db.get_connection() as conn:
                for table in tables:
                    f.write(f"\n--- Investigating {table} ---\n")
                    try:
                        # Try to get top 1 row to see columns
                        query = text(f"SELECT TOP 1 * FROM {table}")
                        df = pd.read_sql(query, conn)
                        f.write(f"Columns found ({len(df.columns)}): {list(df.columns)}\n")
                    except Exception as e:
                        f.write(f"Error reading {table}: {e}\n")
                        
        except Exception as e:
            f.write(f"Fatal DB Error: {e}\n")

    print(f"Schema info written to {output_file}")

if __name__ == "__main__":
    inspect_schema()
