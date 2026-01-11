"""
Production Repository - handles historical production data and orders.
Extracted from DatabaseConnector as part of Repository pattern refactoring.
"""

import logging

import pandas as pd

from .base import BaseRepository

logger = logging.getLogger(__name__)


class ProductionRepository(BaseRepository):
    """
    Repository for production-related queries.
    Handles:
    - Historical production data
    - Product usage statistics
    """

    def get_historical_data(self, use_cache: bool = True, date_from: str = None, date_to: str = None) -> pd.DataFrame:
        """
        Fetch historical production data aggregated by week.
        Joins CtiZlecenieElem with CtiZlecenieNag and CDN.Towary.
        Strictly filters for Raw Materials (CZE_Typ IN (1, 2)).

        Args:
            use_cache: If True, returns cached data if available
            date_from: Optional start date filter (YYYY-MM-DD format)
            date_to: Optional end date filter (YYYY-MM-DD format)

        Note on NOLOCK: Used for read-only reporting queries.
        Risk: May read uncommitted data (dirty reads).
        Benefit: Does not block production ERP operations.
        """
        cache_key = f"historical_data_{date_from}_{date_to}" if (date_from or date_to) else "historical_data"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        base_query = """
        SELECT
            DATEPART(ISO_WEEK, n.CZN_DataRealizacji) as Week,
            YEAR(n.CZN_DataRealizacji) as Year,
            e.CZE_TwrId as TowarId,
            SUM(e.CZE_Ilosc) as Quantity
        FROM dbo.CtiZlecenieElem e WITH (NOLOCK)
        JOIN dbo.CtiZlecenieNag n WITH (NOLOCK) ON e.CZE_CZNId = n.CZN_ID
        JOIN CDN.Towary t WITH (NOLOCK) ON e.CZE_TwrId = t.Twr_TwrId
        WHERE n.CZN_DataRealizacji IS NOT NULL
          AND e.CZE_Typ IN (1, 2)
          AND t.Twr_Typ != 2
        """

        params = {}

        if date_from:
            base_query += " AND n.CZN_DataRealizacji >= :date_from"
            params["date_from"] = date_from
        if date_to:
            base_query += " AND n.CZN_DataRealizacji <= :date_to"
            params["date_to"] = date_to

        base_query += """
        GROUP BY YEAR(n.CZN_DataRealizacji), DATEPART(ISO_WEEK, n.CZN_DataRealizacji), e.CZE_TwrId
        ORDER BY Year, Week
        """

        df = self.execute_query(base_query, params=params if params else None, query_name="get_historical_data")

        if use_cache and not df.empty:
            self._set_cache(cache_key, df)

        return df

    def get_product_usage_stats(self, raw_material_id: int) -> pd.DataFrame:
        """
        Return stats on which Final Products use this Raw Material.
        Joins CtiZlecenieElem, CtiZlecenieNag, and CDN.Towary.
        """
        query = """
        SELECT TOP 20
            t_final.Twr_TwrId as FinalProductId,
            t_final.Twr_Nazwa as FinalProductName,
            t_final.Twr_Kod as FinalProductCode,
            COUNT(DISTINCT n.CZN_ID) as OrderCount,
            SUM(e.CZE_Ilosc) as TotalUsage
        FROM dbo.CtiZlecenieElem e WITH (NOLOCK)
        JOIN dbo.CtiZlecenieNag n WITH (NOLOCK) ON e.CZE_CZNId = n.CZN_ID
        JOIN CDN.Towary t_final WITH (NOLOCK) ON n.CZN_TwrId = t_final.Twr_TwrId
        WHERE e.CZE_TwrId = :raw_material_id
          AND e.CZE_Typ IN (1, 2)
        GROUP BY t_final.Twr_TwrId, t_final.Twr_Nazwa, t_final.Twr_Kod
        ORDER BY TotalUsage DESC
        """
        return self.execute_query(
            query, params={"raw_material_id": raw_material_id}, query_name=f"get_product_usage_stats({raw_material_id})"
        )
