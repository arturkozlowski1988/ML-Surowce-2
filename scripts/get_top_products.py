import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_connector import DatabaseConnector
import pandas as pd

try:
    db = DatabaseConnector()
    query = """
    SELECT TOP 5 
        e.CZE_TwrId as ID, 
        t.Twr_Nazwa as Name, 
        t.Twr_Kod as Code,
        COUNT(*) as Count 
    FROM dbo.CtiZlecenieElem e 
    JOIN CDN.Towary t ON e.CZE_TwrId = t.Twr_TwrId 
    WHERE t.Twr_Typ != 2 
    GROUP BY e.CZE_TwrId, t.Twr_Nazwa, t.Twr_Kod
    ORDER BY Count DESC
    """
    df = db.execute_query(query)
    print(df.to_string())
except Exception as e:
    print(f"Error: {e}")
