"""
Technology Repository - handles BOM (Bill of Materials) and technology queries.
Extracted from DatabaseConnector as part of Repository pattern refactoring.
"""

import logging

import pandas as pd

from .base import BaseRepository

logger = logging.getLogger(__name__)


class TechnologyRepository(BaseRepository):
    """
    Repository for technology and BOM related queries.
    Handles:
    - Bill of Materials (BOM) lookups
    - Technology definitions
    - Stock levels for BOM ingredients
    """

    def get_products_with_technology(self, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetch list of Final Products that have a defined technology (BOM).
        Used for the 'Final Product Analysis' AI mode.
        """
        cache_key = "products_with_technology"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        query = """
        SELECT DISTINCT
            t.Twr_TwrId as FinalProductId,
            t.Twr_Kod as Code,
            t.Twr_Nazwa as Name
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN CDN.Towary t WITH (NOLOCK) ON n.CTN_TwrId = t.Twr_TwrId
        ORDER BY t.Twr_Nazwa
        """
        df = self.execute_query(query, query_name="get_products_with_technology")

        if use_cache and not df.empty:
            self._set_cache(cache_key, df)

        return df

    def get_product_bom(self, final_product_id: int) -> pd.DataFrame:
        """
        Fetch the Bill of Materials (BOM) for a given Final Product.
        Joins CtiTechnolNag, CtiTechnolElem, and CDN.Towary.
        Filters for Ingredients (CTE_Typ IN (1, 2)).
        """
        query = """
        SELECT TOP 100
            elem_t.Twr_Kod as IngredientCode,
            elem_t.Twr_Nazwa as IngredientName,
            e.CTE_Ilosc as QuantityPerUnit,
            elem_t.Twr_JM as Unit,
            e.CTE_Typ as Type
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
        JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
        WHERE n.CTN_TwrId = :final_product_id
          AND e.CTE_Typ IN (1, 2)
        ORDER BY n.CTN_ID DESC, e.CTE_Lp ASC
        """
        return self.execute_query(
            query, params={"final_product_id": final_product_id}, query_name=f"get_product_bom({final_product_id})"
        )

    def get_bom_with_stock(
        self, final_product_id: int, technology_id: int = None, warehouse_ids: list[int] = None
    ) -> pd.DataFrame:
        """
        Fetch BOM for a product along with current stock levels of ingredients.
        Used for AI generation to advise on purchasing.
        """
        warehouse_filter = ""
        if warehouse_ids:
            warehouse_list = ",".join(map(str, warehouse_ids))
            warehouse_filter = f" AND z.TwZ_MagId IN ({warehouse_list})"

        base_query = f"""
        SELECT
            elem_t.Twr_Kod as IngredientCode,
            elem_t.Twr_Nazwa as IngredientName,
            e.CTE_Ilosc as QuantityPerUnit,
            elem_t.Twr_JM as Unit,
            ISNULL(SUM(z.TwZ_Ilosc), 0) as CurrentStock
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
        JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON elem_t.Twr_TwrId = z.TwZ_TwrId{warehouse_filter}
        WHERE n.CTN_TwrId = :final_product_id
          AND e.CTE_Typ IN (1, 2)
          AND elem_t.Twr_Typ != 2
        """

        params = {"final_product_id": final_product_id}

        if technology_id is not None:
            base_query += " AND n.CTN_ID = :technology_id"
            params["technology_id"] = int(technology_id)

        base_query += """
        GROUP BY elem_t.Twr_Kod, elem_t.Twr_Nazwa, e.CTE_Ilosc, elem_t.Twr_JM
        ORDER BY e.CTE_Ilosc DESC
        """

        return self.execute_query(base_query, params=params, query_name=f"get_bom_with_stock({final_product_id})")

    def get_bom_with_warehouse_breakdown(self, final_product_id: int, technology_id: int = None) -> pd.DataFrame:
        """
        Fetch BOM for a product with stock breakdown per warehouse.
        Used by AI to provide recommendations considering stock in other warehouses.
        """
        tech_filter = ""
        params = {"final_product_id": int(final_product_id)}

        if technology_id is not None:
            tech_filter = " AND n.CTN_ID = :technology_id"
            params["technology_id"] = int(technology_id)

        query = f"""
        WITH BomItems AS (
            SELECT DISTINCT
                elem_t.Twr_TwrId as IngredientId,
                elem_t.Twr_Kod as IngredientCode,
                elem_t.Twr_Nazwa as IngredientName,
                e.CTE_Ilosc as QuantityPerUnit,
                elem_t.Twr_JM as Unit
            FROM dbo.CtiTechnolNag n WITH (NOLOCK)
            JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
            JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
            WHERE n.CTN_TwrId = :final_product_id
              AND e.CTE_Typ IN (1, 2)
              AND elem_t.Twr_Typ != 2
              {tech_filter}
        )
        SELECT
            b.IngredientCode,
            b.IngredientName,
            b.QuantityPerUnit,
            b.Unit,
            m.Mag_Symbol as MagSymbol,
            m.Mag_Nazwa as MagName,
            ISNULL(z.TwZ_Ilosc, 0) as StockInWarehouse,
            (SELECT ISNULL(SUM(z2.TwZ_Ilosc), 0)
             FROM CDN.TwrZasoby z2
             WHERE z2.TwZ_TwrId = b.IngredientId) as TotalStock
        FROM BomItems b
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON b.IngredientId = z.TwZ_TwrId
        LEFT JOIN CDN.Magazyny m WITH (NOLOCK) ON z.TwZ_MagId = m.Mag_MagId
        WHERE z.TwZ_Ilosc > 0 OR z.TwZ_Ilosc IS NULL
        ORDER BY b.IngredientCode, m.Mag_Symbol
        """

        return self.execute_query(
            query, params=params, query_name=f"get_bom_with_warehouse_breakdown({final_product_id})"
        )
