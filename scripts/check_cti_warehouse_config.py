"""
Script to check CTI warehouse configuration tables and compare with cdn_mietex.
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

conn_str = os.getenv("DB_CONN_STR")
engine = create_engine(conn_str)

print("=" * 60)
print("CTI Warehouse Configuration Analysis")
print("=" * 60)

queries = {
    # CtiKonfigMag structure
    "CtiKonfigMag columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CtiKonfigMag'
        ORDER BY ORDINAL_POSITION
    """,
    # CtiKonfigMag data
    "CtiKonfigMag data (all)": """
        SELECT * FROM dbo.CtiKonfigMag ORDER BY 1
    """,
    # CTIMagPiny structure
    "CTIMagPiny columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CTIMagPiny'
        ORDER BY ORDINAL_POSITION
    """,
    # CTIMagPiny data (sample)
    "CTIMagPiny data (sample)": """
        SELECT TOP 20 * FROM dbo.CTIMagPiny
    """,
    # Check CtiZlecenieNag for warehouse columns
    "CtiZlecenieNag warehouse related columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'CtiZlecenieNag'
          AND (COLUMN_NAME LIKE '%Mag%' OR COLUMN_NAME LIKE '%Surowiec%' OR COLUMN_NAME LIKE '%Produkt%')
        ORDER BY ORDINAL_POSITION
    """,
    # Production orders with warehouse info
    "Sample production orders with warehouses": """
        SELECT TOP 20
            n.CZN_ID,
            n.CZN_Nr,
            n.CZN_DomyslneMagSur,
            t.Twr_Nazwa as ProduktName
        FROM dbo.CtiZlecenieNag n WITH (NOLOCK)
        JOIN CDN.Towary t ON n.CZN_TwrId = t.Twr_TwrId
        ORDER BY n.CZN_ID DESC
    """,
    # Unique warehouse configurations in production
    "Warehouse configurations in production orders": """
        SELECT DISTINCT
            CZN_DomyslneMagSur,
            COUNT(*) as OrderCount
        FROM dbo.CtiZlecenieNag
        GROUP BY CZN_DomyslneMagSur
        ORDER BY OrderCount DESC
    """,
}

for name, query in queries.items():
    print(f"\n--- {name} ---")
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            if df.empty:
                print("(No results)")
            else:
                print(df.to_string(index=False))
    except Exception as e:
        print(f"ERROR: {e}")


# Now check cdn_mietex database
print("\n" + "=" * 60)
print("Checking cdn_mietex database")
print("=" * 60)

# Modify connection string for cdn_mietex
conn_str_mietex = conn_str.replace("cdn_test", "cdn_mietex")
try:
    engine_mietex = create_engine(conn_str_mietex)

    mietex_queries = {
        "cdn_mietex: Warehouses": """
            SELECT
                m.Mag_MagId,
                m.Mag_Symbol,
                m.Mag_Nazwa,
                COUNT(DISTINCT z.TwZ_TwrId) as ProductCount,
                SUM(z.TwZ_Ilosc) as TotalStock
            FROM CDN.Magazyny m
            LEFT JOIN CDN.TwrZasoby z ON m.Mag_MagId = z.TwZ_MagId
            GROUP BY m.Mag_MagId, m.Mag_Symbol, m.Mag_Nazwa
            HAVING SUM(z.TwZ_Ilosc) > 0
            ORDER BY TotalStock DESC
        """,
        "cdn_mietex: CtiKonfigMag": """
            SELECT * FROM dbo.CtiKonfigMag ORDER BY 1
        """,
    }

    for name, query in mietex_queries.items():
        print(f"\n--- {name} ---")
        try:
            with engine_mietex.connect() as conn:
                df = pd.read_sql(text(query), conn)
                if df.empty:
                    print("(No results)")
                else:
                    print(df.to_string(index=False))
        except Exception as e:
            print(f"ERROR: {e}")
except Exception as e:
    print(f"Cannot connect to cdn_mietex: {e}")
