import sys
import os
import io

# Fix encoding for Windows console (CP1250 -> UTF-8)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from db_connector import DatabaseConnector

try:
    print("Initializing DatabaseConnector...")
    db = DatabaseConnector()
    print("Testing connection...")
    if db.test_connection():
        print("SUCCESS: Connection verified!")
        # Print the connection string used (masked)
        print(f"Connection string used: {db.conn_str.replace('Cti123456%26', '******')}")
    else:
        print("FAILURE: Connection test returned False")
except Exception as e:
    print(f"FAILURE: Exception occurred: {e}")
