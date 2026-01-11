"""
Demo Data Connector - Provides data from JSON files for demo mode.
Used when no database connection is available (e.g., academic presentations).
"""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("DemoDataConnector")

# Path to demo data
PROJECT_ROOT = Path(__file__).parent.parent
DEMO_DATA_FILE = PROJECT_ROOT / "data" / "demo" / "demo_dataset.json"


class DemoDataConnector:
    """
    A connector that provides data from JSON files instead of database.
    Mimics the interface of DatabaseConnector for seamless integration.
    """

    def __init__(self, database_name: str = "demo"):
        """Initialize demo connector."""
        self.database_name = database_name
        self._data = None
        self._load_demo_data()
        logger.info("DemoDataConnector initialized (demo mode)")

    def _load_demo_data(self):
        """Load demo data from JSON file."""
        if DEMO_DATA_FILE.exists():
            try:
                with open(DEMO_DATA_FILE, encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info(f"Loaded demo data from {DEMO_DATA_FILE}")
            except Exception as e:
                logger.error(f"Error loading demo data: {e}")
                self._data = {}
        else:
            logger.warning(f"Demo data file not found: {DEMO_DATA_FILE}")
            self._data = {}

    def test_connection(self) -> bool:
        """Always returns True for demo mode."""
        return self._data is not None and len(self._data) > 0

    def get_historical_data(self, use_cache: bool = True, date_from: str = None, date_to: str = None) -> pd.DataFrame:
        """Returns historical data from demo dataset."""
        data = self._data.get("historical", [])
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Apply date filters if provided
        if date_from and "Year" in df.columns and "Week" in df.columns:
            # Simple filtering by year/week
            pass  # Demo data doesn't need strict filtering

        return df

    def get_current_stock(self, use_cache: bool = True, warehouse_ids: list[int] = None) -> pd.DataFrame:
        """Returns current stock from demo dataset."""
        data = self._data.get("stock", [])
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Simulate warehouse filtering (demo data has all warehouses)
        # In demo mode, we don't actually filter
        return df

    def get_warehouses(self, use_cache: bool = True, only_with_stock: bool = True) -> pd.DataFrame:
        """Returns warehouses from demo dataset."""
        data = self._data.get("warehouses", [])
        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)

    def get_products_with_technology(self, use_cache: bool = True) -> pd.DataFrame:
        """Returns products with technology from demo dataset."""
        data = self._data.get("products_with_tech", [])
        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)

    def get_bom_with_stock(
        self, final_product_id: int, technology_id: int = None, warehouse_ids: list[int] = None
    ) -> pd.DataFrame:
        """Returns BOM data from demo dataset."""
        data = self._data.get("bom", [])
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Filter by product if we have FinalProductId column
        if "FinalProductId" in df.columns:
            df = df[df["FinalProductId"] == final_product_id]

        return df

    def get_bom_with_warehouse_breakdown(self, final_product_id: int, technology_id: int = None) -> pd.DataFrame:
        """Returns BOM with warehouse breakdown (simplified for demo)."""
        # Demo mode doesn't have full warehouse breakdown
        return pd.DataFrame()

    def get_product_usage_stats(self, raw_material_id: int) -> pd.DataFrame:
        """Returns product usage stats (simplified for demo)."""
        # Demo mode doesn't have full usage stats
        return pd.DataFrame()

    def get_diagnostics_stats(self) -> dict:
        """Returns diagnostics (demo mode)."""
        return {"total_queries": 0, "avg_duration": 0, "mode": "demo"}

    def clear_cache(self, cache_key: str = None):
        """No-op for demo mode."""
        pass

    def clear_database_cache(self):
        """No-op for demo mode."""
        pass


def check_demo_data_available() -> tuple:
    """
    Checks if demo data is available.

    Returns:
        tuple: (is_available: bool, message: str)
    """
    if DEMO_DATA_FILE.exists():
        try:
            with open(DEMO_DATA_FILE, encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            counts = metadata.get("record_counts", {})

            return True, f"Demo data available ({counts.get('stock', 0)} products)"
        except Exception as e:
            return False, f"Error reading demo data: {e}"
    else:
        return False, "Demo data file not found"
