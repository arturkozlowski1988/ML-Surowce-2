"""
Stock Repository - handles warehouse and inventory queries.
Extracted from DatabaseConnector as part of Repository pattern refactoring.
"""

import logging

import pandas as pd
from sqlalchemy.engine import Engine

from .base import BaseRepository

logger = logging.getLogger(__name__)


class StockRepository(BaseRepository):
    """
    Repository for stock and warehouse related queries.
    Handles:
    - Current stock levels (TwrZasoby/Towary)
    - Warehouse listings
    - Stock by warehouse breakdown
    """

    def __init__(self, engine: Engine, database_name: str = None, diagnostics=None):
        super().__init__(engine, database_name, diagnostics)

    def get_warehouses(self, use_cache: bool = True, only_with_stock: bool = True) -> pd.DataFrame:
        """
        Fetch list of available warehouses with stock counts.

        Args:
            use_cache: If True, returns cached data if available
            only_with_stock: If True, returns only warehouses with stock > 0

        Returns:
            DataFrame with columns: MagId, Symbol, Name, ProductCount, TotalStock
        """
        cache_key = f"warehouses_{only_with_stock}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        query = """
            SELECT
                m.Mag_MagId as MagId,
                m.Mag_Symbol as Symbol,
                m.Mag_Nazwa as Name,
                COUNT(DISTINCT tz.TwZ_TwrId) as ProductCount,
                ISNULL(SUM(tz.TwZ_Ilosc), 0) as TotalStock
            FROM CDN.Magazyny m WITH (NOLOCK)
            LEFT JOIN dbo.TwrZasoby tz WITH (NOLOCK) ON tz.TwZ_MagId = m.Mag_MagId
            WHERE m.Mag_Typ = 1  -- Standard warehouses only
            GROUP BY m.Mag_MagId, m.Mag_Symbol, m.Mag_Nazwa
        """

        if only_with_stock:
            query += " HAVING ISNULL(SUM(tz.TwZ_Ilosc), 0) > 0"

        query += " ORDER BY m.Mag_Symbol"

        df = self.execute_query(query, query_name="get_warehouses")

        if use_cache and not df.empty:
            self._set_cache(cache_key, df)

        return df

    def get_current_stock(self, use_cache: bool = True, warehouse_ids: list[int] = None) -> pd.DataFrame:
        """
        Fetch current stock levels from TwrZasoby/Towary.
        Only includes items defined as Raw Materials in production orders.
        Excludes explicit Services (Twr_Typ = 2).

        Args:
            use_cache: If True, returns cached data if available
            warehouse_ids: Optional list of warehouse IDs to filter by

        Returns:
            DataFrame with stock information
        """
        cache_key = f"current_stock_{warehouse_ids}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        # Base query for raw materials used in production
        query = """
            WITH RawMaterialsUsedInProduction AS (
                SELECT DISTINCT CZE_TwrId as TwrId
                FROM dbo.CtiZlecenieElem WITH (NOLOCK)
                WHERE CZE_Typ IN (1, 2)  -- Input materials only
            )
            SELECT
                t.Twr_TwrId as TowarId,
                t.Twr_Kod as KodKreskowy,
                t.Twr_Nazwa as Nazwa,
                t.Twr_JM as JM,
        """

        if warehouse_ids:
            query += """
                ISNULL(SUM(CASE WHEN tz.TwZ_MagId IN :warehouse_ids
                           THEN tz.TwZ_Ilosc ELSE 0 END), 0) as Quantity
            """
        else:
            query += """
                ISNULL(SUM(tz.TwZ_Ilosc), 0) as Quantity
            """

        query += """
            FROM CDN.Towary t WITH (NOLOCK)
            INNER JOIN RawMaterialsUsedInProduction rm ON t.Twr_TwrId = rm.TwrId
            LEFT JOIN dbo.TwrZasoby tz WITH (NOLOCK) ON t.Twr_TwrId = tz.TwZ_TwrId
            WHERE t.Twr_Typ <> 2  -- Exclude services
        """

        if warehouse_ids:
            query += " AND (tz.TwZ_MagId IN :warehouse_ids OR tz.TwZ_MagId IS NULL)"

        query += """
            GROUP BY t.Twr_TwrId, t.Twr_Kod, t.Twr_Nazwa, t.Twr_JM
            ORDER BY t.Twr_Nazwa
        """

        params = {}
        if warehouse_ids:
            params["warehouse_ids"] = tuple(warehouse_ids)

        df = self.execute_query(query, params=params, query_name="get_current_stock")

        if use_cache and not df.empty:
            self._set_cache(cache_key, df)

        return df

    def get_stock_by_warehouse(self, product_id: int = None) -> pd.DataFrame:
        """
        Get stock breakdown by warehouse for a product or all products.

        Args:
            product_id: Optional product ID to filter

        Returns:
            DataFrame with per-warehouse stock breakdown
        """
        query = """
            SELECT
                t.Twr_TwrId as TowarId,
                t.Twr_Kod as KodKreskowy,
                t.Twr_Nazwa as Nazwa,
                m.Mag_MagId as MagId,
                m.Mag_Symbol as MagSymbol,
                m.Mag_Nazwa as MagName,
                ISNULL(tz.TwZ_Ilosc, 0) as StockInWarehouse
            FROM CDN.Towary t WITH (NOLOCK)
            CROSS JOIN CDN.Magazyny m WITH (NOLOCK)
            LEFT JOIN dbo.TwrZasoby tz WITH (NOLOCK)
                ON t.Twr_TwrId = tz.TwZ_TwrId AND m.Mag_MagId = tz.TwZ_MagId
            WHERE m.Mag_Typ = 1
        """

        params = {}
        if product_id:
            query += " AND t.Twr_TwrId = :product_id"
            params["product_id"] = product_id

        query += " ORDER BY t.Twr_Nazwa, m.Mag_Symbol"

        return self.execute_query(query, params=params, query_name="get_stock_by_warehouse")
