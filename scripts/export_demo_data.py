"""
Script to export and anonymize data from cdn_mietex for demo purposes.
Creates JSON files that can be used in demo mode without database connection.
"""

import sys
sys.path.insert(0, '.')

from src.db_connector import DatabaseConnector
import pandas as pd
import json
import random
from pathlib import Path

# Output directory
DEMO_DATA_DIR = Path("data/demo")
DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)

print("🔄 Connecting to cdn_mietex...")
db = DatabaseConnector(database_name='cdn_mietex')
print(f"✅ Connected to: {db.database_name}")

# ==========================================
# 1. Fetch all data
# ==========================================
print("\n📊 Fetching data...")

df_hist = db.get_historical_data()
df_stock = db.get_current_stock()
df_warehouses = db.get_warehouses()
df_tech = db.get_products_with_technology()

print(f"   Historical: {len(df_hist)} rows")
print(f"   Stock: {len(df_stock)} rows")
print(f"   Warehouses: {len(df_warehouses)} rows")
print(f"   Products with tech: {len(df_tech)} rows")

# Get BOM for first few products
bom_data = []
if not df_tech.empty:
    for i in range(min(5, len(df_tech))):
        prod_id = int(df_tech.iloc[i]['FinalProductId'])
        df_bom = db.get_bom_with_stock(prod_id)
        if not df_bom.empty:
            df_bom['FinalProductId'] = prod_id
            bom_data.append(df_bom)

if bom_data:
    df_bom_all = pd.concat(bom_data, ignore_index=True)
else:
    df_bom_all = pd.DataFrame()

print(f"   BOM items: {len(df_bom_all)} rows")

# ==========================================
# 2. Anonymize data
# ==========================================
print("\n🔒 Anonymizing data...")

# Product name anonymization mapping
PRODUCT_PREFIXES = ["Surowiec", "Materiał", "Komponent", "Element", "Część"]
PRODUCT_SUFFIXES = ["A", "B", "C", "X", "Y", "Z", "Alpha", "Beta", "Gamma"]

# Warehouse name anonymization
WAREHOUSE_NAMES = {
    "MAG1": "Magazyn Główny",
    "MAG2": "Magazyn Produkcja",
    "MAG3": "Magazyn WIP",
    "MAG4": "Magazyn Gotowe",
    "MAG5": "Magazyn Reklamacje",
    "MAG6": "Magazyn Zewnętrzny"
}

def anonymize_product_name(name, idx):
    """Anonymize product name."""
    prefix = PRODUCT_PREFIXES[idx % len(PRODUCT_PREFIXES)]
    suffix = PRODUCT_SUFFIXES[idx % len(PRODUCT_SUFFIXES)]
    num = (idx * 7 + 13) % 1000
    return f"{prefix} {suffix}-{num:03d}"

def anonymize_product_code(code, idx):
    """Anonymize product code."""
    return f"PRD-{idx:04d}"

# Anonymize stock data
if not df_stock.empty:
    code_map = {}
    for i, row in df_stock.iterrows():
        old_code = row['Code']
        if old_code not in code_map:
            idx = len(code_map)
            code_map[old_code] = {
                'new_code': anonymize_product_code(old_code, idx),
                'new_name': anonymize_product_name(row['Name'], idx)
            }
        df_stock.at[i, 'Code'] = code_map[old_code]['new_code']
        df_stock.at[i, 'Name'] = code_map[old_code]['new_name']
    
    # Add some randomness to stock levels
    df_stock['StockLevel'] = df_stock['StockLevel'].apply(
        lambda x: max(0, x * random.uniform(0.8, 1.2))
    )

# Anonymize historical data (just randomize TowarId mapping)
if not df_hist.empty:
    unique_ids = df_hist['TowarId'].unique()
    id_map = {old_id: 1000 + i for i, old_id in enumerate(unique_ids)}
    df_hist['TowarId'] = df_hist['TowarId'].map(id_map)
    
    # Randomize quantities slightly
    df_hist['Quantity'] = df_hist['Quantity'].apply(
        lambda x: max(0, x * random.uniform(0.9, 1.1))
    )

# Anonymize warehouses
if not df_warehouses.empty:
    for i, row in df_warehouses.iterrows():
        mag_key = f"MAG{i+1}"
        if mag_key in WAREHOUSE_NAMES:
            df_warehouses.at[i, 'Symbol'] = mag_key
            df_warehouses.at[i, 'Name'] = WAREHOUSE_NAMES[mag_key]
        else:
            df_warehouses.at[i, 'Symbol'] = f"MAG{i+1}"
            df_warehouses.at[i, 'Name'] = f"Magazyn {i+1}"

# Anonymize technology products
if not df_tech.empty:
    for i, row in df_tech.iterrows():
        df_tech.at[i, 'Code'] = f"PROD-{i:03d}"
        df_tech.at[i, 'Name'] = f"Wyrób Gotowy {chr(65 + i % 26)}-{i:02d}"

# Anonymize BOM
if not df_bom_all.empty:
    for i, row in df_bom_all.iterrows():
        df_bom_all.at[i, 'IngredientCode'] = f"ING-{i:04d}"
        df_bom_all.at[i, 'IngredientName'] = anonymize_product_name(row['IngredientName'], i)

# ==========================================
# 3. Save to JSON files
# ==========================================
print("\n💾 Saving demo data...")

def df_to_json_records(df):
    """Convert DataFrame to JSON-serializable records."""
    return json.loads(df.to_json(orient='records', date_format='iso'))

demo_data = {
    'historical': df_to_json_records(df_hist) if not df_hist.empty else [],
    'stock': df_to_json_records(df_stock) if not df_stock.empty else [],
    'warehouses': df_to_json_records(df_warehouses) if not df_warehouses.empty else [],
    'products_with_tech': df_to_json_records(df_tech) if not df_tech.empty else [],
    'bom': df_to_json_records(df_bom_all) if not df_bom_all.empty else [],
    'metadata': {
        'source': 'cdn_mietex (anonymized)',
        'created': pd.Timestamp.now().isoformat(),
        'record_counts': {
            'historical': len(df_hist),
            'stock': len(df_stock),
            'warehouses': len(df_warehouses),
            'products_with_tech': len(df_tech),
            'bom': len(df_bom_all)
        }
    }
}

output_file = DEMO_DATA_DIR / "demo_dataset.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(demo_data, f, indent=2, ensure_ascii=False)

print(f"✅ Saved to: {output_file}")
print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")

# Also create a product map for display
if not df_stock.empty:
    product_map = dict(zip(df_stock['TowarId'], df_stock['Name'] + " (" + df_stock['Code'] + ")"))
    product_map_file = DEMO_DATA_DIR / "product_map.json"
    with open(product_map_file, 'w', encoding='utf-8') as f:
        json.dump(product_map, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved product map: {product_map_file}")

print("\n🎉 Done! Demo data ready for use.")
