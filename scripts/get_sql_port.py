import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from db_connector import DatabaseConnector

try:
    print("Initializing DatabaseConnector...")
    db = DatabaseConnector()
    print("Querying port...")
    
    # Query to get all TCP listeners
    query = """
    SELECT port
    FROM sys.dm_tcp_listener_states
    WHERE type_desc = 'TSQL'
    """
    
    df = db.execute_query(query)
    if not df.empty:
        print("Listener Info:")
        print(df)
        port = df.iloc[0]['port']
        print(f"DETECTED_PORT={port}")
    else:
        print("Could not determine port (no TSQL listeners found)")
        
except Exception as e:
    print(f"FAILURE: Exception occurred: {e}")
