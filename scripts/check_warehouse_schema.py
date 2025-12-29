"""
Script to check warehouse-related tables in the database.
Explores CDN.Magazyny, CDN.TwrZasoby and related tables.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
import pandas as pd

load_dotenv()

conn_str = os.getenv('DB_CONN_STR')
engine = create_engine(conn_str)

print("=" * 60)
print("Checking Warehouse Schema in cdn_test")
print("=" * 60)

queries = {
    # Check CDN.Magazyny table (warehouses)
    "CDN.Magazyny columns": """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'CDN' AND TABLE_NAME = 'Magazyny'
        ORDER BY ORDINAL_POSITION
    """,
    
    # Sample warehouses
    "Sample Warehouses": """
        SELECT TOP 20 * FROM CDN.Magazyny
    """,
    
    # Check TwrZasoby columns (stock per warehouse)
    "CDN.TwrZasoby columns": """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'CDN' AND TABLE_NAME = 'TwrZasoby'
        ORDER BY ORDINAL_POSITION
    """,
    
    # Sample stock data with warehouse info
    "Sample Stock with Warehouse": """
        SELECT TOP 20 
            z.TwZ_TwrId, 
            z.TwZ_MagId, 
            z.TwZ_Ilosc,
            m.Mag_Symbol,
            m.Mag_Nazwa,
            t.Twr_Kod,
            t.Twr_Nazwa
        FROM CDN.TwrZasoby z
        JOIN CDN.Magazyny m ON z.TwZ_MagId = m.Mag_MagId
        JOIN CDN.Towary t ON z.TwZ_TwrId = t.Twr_TwrId
        WHERE z.TwZ_Ilosc > 0
    """,
    
    # Total stock grouped by warehouse
    "Stock by Warehouse Summary": """
        SELECT 
            m.Mag_MagId,
            m.Mag_Symbol,
            m.Mag_Nazwa,
            COUNT(DISTINCT z.TwZ_TwrId) as ProductCount,
            SUM(z.TwZ_Ilosc) as TotalStock
        FROM CDN.Magazyny m
        LEFT JOIN CDN.TwrZasoby z ON m.Mag_MagId = z.TwZ_MagId
        GROUP BY m.Mag_MagId, m.Mag_Symbol, m.Mag_Nazwa
        ORDER BY m.Mag_Symbol
    """,
    
    # Check for warehouse configuration in CTI tables
    "CTI Configuration Tables": """
        SELECT TABLE_NAME, TABLE_SCHEMA
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME LIKE '%Cti%Mag%' OR TABLE_NAME LIKE '%Cti%Config%'
        ORDER BY TABLE_NAME
    """,
    
    # Check CtiZlecenieNag for warehouse references
    "CtiZlecenieNag warehouse columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'CtiZlecenieNag' AND COLUMN_NAME LIKE '%Mag%'
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
