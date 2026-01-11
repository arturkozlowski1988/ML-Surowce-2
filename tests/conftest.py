"""
Pytest fixtures and configuration for AI Supply Assistant tests.
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Mock Database Fixture
# ============================================================================


class MockDatabaseConnector:
    """Mock database connector for testing without real database connection."""

    def __init__(self):
        self.database_name = "test_db"
        self._cache = {}

    def test_connection(self) -> bool:
        return True

    def get_current_stock(self, use_cache: bool = True, warehouse_ids: list = None) -> pd.DataFrame:
        """Return mock stock data."""
        return pd.DataFrame(
            {
                "TowarId": [1, 2, 3],
                "KodKreskowy": ["CODE001", "CODE002", "CODE003"],
                "Nazwa": ["Material A", "Material B", "Material C"],
                "JM": ["kg", "kg", "szt"],
                "Quantity": [100.0, 250.0, 500.0],
            }
        )

    def get_warehouses(self, use_cache: bool = True, only_with_stock: bool = True) -> pd.DataFrame:
        """Return mock warehouse data."""
        return pd.DataFrame(
            {
                "MagId": [1, 2],
                "Symbol": ["MAG1", "MAG2"],
                "Name": ["Warehouse 1", "Warehouse 2"],
                "ProductCount": [10, 5],
                "TotalStock": [1000.0, 500.0],
            }
        )

    def get_historical_data(self, use_cache: bool = True, date_from: str = None, date_to: str = None) -> pd.DataFrame:
        """Return mock historical production data."""
        np.random.seed(42)
        rows = []
        base_date = datetime(2024, 1, 1)

        for product_id in range(1, 4):
            for week in range(52):
                date = pd.Timestamp(base_date) + pd.Timedelta(weeks=week)
                qty = 50 + product_id * 20 + np.random.normal(0, 10)
                rows.append(
                    {
                        "TowarId": product_id,
                        "Year": date.isocalendar()[0],
                        "Week": date.isocalendar()[1],
                        "Quantity": max(0, round(qty, 2)),
                    }
                )

        return pd.DataFrame(rows)

    def execute_query(self, query: str, params=None, query_name: str = "test") -> pd.DataFrame:
        """Mock query execution."""
        return pd.DataFrame()

    def clear_cache(self, cache_key: str = None):
        """Clear mock cache."""
        if cache_key:
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()


@pytest.fixture
def mock_db():
    """Provide mock database connector for tests."""
    return MockDatabaseConnector()


# ============================================================================
# Synthetic Data Fixtures
# ============================================================================


@pytest.fixture
def synthetic_time_series():
    """Generate synthetic time series data for ML testing."""
    np.random.seed(42)
    rows = []
    base_date = datetime(2024, 1, 1)

    for product_id in range(1, 4):
        base_demand = 50 + product_id * 20
        for week in range(52):
            seasonal = 15 * np.sin(2 * np.pi * week / 13)
            noise = np.random.normal(0, 5)
            qty = max(0, base_demand + 0.5 * week + seasonal + noise)

            date = pd.Timestamp(base_date) + pd.Timedelta(weeks=week)
            rows.append(
                {
                    "TowarId": product_id,
                    "Year": date.isocalendar()[0],
                    "Week": date.isocalendar()[1],
                    "Quantity": round(qty, 2),
                    "Date": date,
                }
            )

    return pd.DataFrame(rows)


@pytest.fixture
def sample_stock_data():
    """Provide sample stock data for testing."""
    return pd.DataFrame(
        {
            "TowarId": [1, 2, 3, 4, 5],
            "KodKreskowy": ["MAT001", "MAT002", "MAT003", "MAT004", "MAT005"],
            "Nazwa": ["Steel Plate", "Aluminum Sheet", "Copper Wire", "Plastic Granules", "Rubber Seal"],
            "JM": ["kg", "kg", "m", "kg", "szt"],
            "Quantity": [500.0, 200.0, 1000.0, 350.0, 2500.0],
        }
    )


# ============================================================================
# Security Test Fixtures
# ============================================================================


@pytest.fixture
def encryption_key():
    """Generate encryption key for security tests."""
    from src.security.encryption import ConfigEncryption

    return ConfigEncryption.generate_master_key()


@pytest.fixture
def temp_audit_log(tmp_path):
    """Provide temporary path for audit log testing."""
    return str(tmp_path / "test_audit.log")


# ============================================================================
# Skip Markers for Conditional Tests
# ============================================================================


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests requiring database")
    config.addinivalue_line("markers", "security: marks security-related tests")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if database is not available."""
    skip_integration = pytest.mark.skip(reason="Database not available")

    for item in items:
        if "integration" in item.keywords:
            # Try to check database availability
            try:
                from src.db_connector import DatabaseConnector

                db = DatabaseConnector(enable_audit=False)
                db.test_connection()
            except Exception:
                item.add_marker(skip_integration)
