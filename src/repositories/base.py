"""
Base Repository class for database operations.
Provides common functionality for all repository classes.
"""

import logging
import time
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base class for database repositories.
    Provides common query execution, caching, and diagnostics functionality.
    """

    # Shared cache across all repository instances
    _cache: dict[str, pd.DataFrame] = {}
    _cache_timestamps: dict[str, float] = {}
    _cache_ttl: int = 300  # 5 minutes default

    def __init__(self, engine: Engine, database_name: str = None, diagnostics=None):
        """
        Initialize base repository.

        Args:
            engine: SQLAlchemy engine for database connection
            database_name: Name of the database (for cache keying)
            diagnostics: Optional QueryDiagnostics instance for performance logging
        """
        self.engine = engine
        self.database_name = database_name or "default"
        self.diagnostics = diagnostics

    def execute_query(self, query: str, params: dict[str, Any] = None, query_name: str = "unnamed") -> pd.DataFrame:
        """
        Execute a SQL query and return results as DataFrame.

        Args:
            query: SQL query string
            params: Optional dictionary of query parameters
            query_name: Name for diagnostics logging

        Returns:
            pandas DataFrame with query results
        """
        start_time = time.time()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                df = pd.DataFrame(result.fetchall(), columns=result.keys())

            duration = time.time() - start_time

            if self.diagnostics:
                self.diagnostics.log_query(query_name, duration, len(df))

            return df

        except Exception as e:
            logger.error(f"Query '{query_name}' failed: {e}")
            raise

    def _get_cache_key(self, base_key: str) -> str:
        """Create database-specific cache key."""
        return f"{self.database_name}:{base_key}"

    def _get_from_cache(self, cache_key: str) -> pd.DataFrame | None:
        """Retrieve data from cache if valid."""
        full_key = self._get_cache_key(cache_key)

        if full_key in self._cache:
            timestamp = self._cache_timestamps.get(full_key, 0)
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return self._cache[full_key].copy()
            else:
                # Cache expired
                del self._cache[full_key]
                del self._cache_timestamps[full_key]

        return None

    def _set_cache(self, cache_key: str, data: pd.DataFrame):
        """Store data in cache."""
        full_key = self._get_cache_key(cache_key)
        self._cache[full_key] = data.copy()
        self._cache_timestamps[full_key] = time.time()

    def clear_cache(self, cache_key: str = None):
        """Clear cache - all or specific key."""
        if cache_key:
            full_key = self._get_cache_key(cache_key)
            self._cache.pop(full_key, None)
            self._cache_timestamps.pop(full_key, None)
        else:
            # Clear all cache for this database
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{self.database_name}:")]
            for key in keys_to_remove:
                del self._cache[key]
                self._cache_timestamps.pop(key, None)
