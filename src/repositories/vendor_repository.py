"""
Vendor Repository - handles vendor delivery stats and lead times.
Extracted from DatabaseConnector as part of Repository pattern refactoring.
"""

import logging

import pandas as pd

from .base import BaseRepository

logger = logging.getLogger(__name__)


class VendorRepository(BaseRepository):
    """
    Repository for vendor-related queries.
    Handles:
    - Vendor delivery performance
    - Product delivery information
    - Lead times
    """

    def get_vendor_delivery_stats(self, vendor_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Analyze vendor delivery performance based on CDN.TraNag.
        Calculates average delivery delays for supplier evaluation.

        Args:
            vendor_id: Optional specific vendor ID to analyze
            use_cache: If True, returns cached data if available

        Returns:
            DataFrame with vendor performance metrics and rating
        """
        cache_key = f"vendor_stats_{vendor_id or 'all'}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        vendor_filter = ""
        params = {}
        if vendor_id is not None:
            vendor_filter = "AND t.TrN_KnTId = :vendor_id"
            params["vendor_id"] = vendor_id

        query = f"""
        SELECT
            k.Knt_KntId as VendorId,
            k.Knt_Kod as VendorCode,
            k.Knt_Nazwa1 as VendorName,
            COUNT(*) as DeliveryCount,
            AVG(DATEDIFF(day, t.TrN_DataDoc, t.TrN_DataOtrz)) as AvgDelayDays,
            SUM(CASE WHEN DATEDIFF(day, t.TrN_DataDoc, t.TrN_DataOtrz) <= 0
                THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as OnTimePercent
        FROM CDN.TraNag t WITH (NOLOCK)
        JOIN CDN.Kontrahenci k WITH (NOLOCK) ON t.TrN_KnTId = k.Knt_KntId
        WHERE t.TrN_TypDokumentu = 301
          AND t.TrN_DataOtrz IS NOT NULL
          AND t.TrN_DataDoc IS NOT NULL
          {vendor_filter}
        GROUP BY k.Knt_KntId, k.Knt_Kod, k.Knt_Nazwa1
        HAVING COUNT(*) >= 3
        ORDER BY AvgDelayDays ASC
        """

        df = self.execute_query(query, params=params if params else None, query_name="get_vendor_delivery_stats")

        if not df.empty:

            def calculate_rating(row):
                if row["AvgDelayDays"] <= 0 and row["OnTimePercent"] >= 90:
                    return "A"
                elif row["AvgDelayDays"] <= 3 and row["OnTimePercent"] >= 70:
                    return "B"
                elif row["AvgDelayDays"] <= 7 and row["OnTimePercent"] >= 50:
                    return "C"
                else:
                    return "D"

            df["Rating"] = df.apply(calculate_rating, axis=1)
            df["AvgDelayDays"] = df["AvgDelayDays"].round(1)
            df["OnTimePercent"] = df["OnTimePercent"].round(1)

            if use_cache:
                self._set_cache(cache_key, df)

        return df

    def get_product_delivery_info(self, product_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetch delivery information from CtiDelivery table.
        Includes vendor info, delivery times, costs, and order limits.
        """
        cache_key = f"delivery_info_{product_id or 'all'}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        product_filter = ""
        params = {}
        if product_id is not None:
            product_filter = "AND cd.CD_TwrId = :product_id"
            params["product_id"] = product_id

        query = f"""
        SELECT
            cd.CD_TwrId AS ProductId,
            t.Twr_Kod AS ProductCode,
            t.Twr_Nazwa AS ProductName,
            cd.CD_KntId AS VendorId,
            k.Knt_Kod AS VendorCode,
            k.Knt_Nazwa1 AS VendorName,
            cd.CD_DefaultProvider AS IsDefaultVendor,
            cd.CD_MinDeliveryTime AS DeliveryTime_Min,
            cd.CD_OptimumDeliveryTime AS DeliveryTime_Optimum,
            cd.CD_MaxDeliveryTime AS DeliveryTime_Max,
            cd.CD_MinDeliveryCost AS DeliveryCost_Min,
            cd.CD_OptimumDeliveryCost AS DeliveryCost_Optimum,
            cd.CD_MaxDeliveryCost AS DeliveryCost_Max,
            cd.CD_MinProductionTime AS ProductionTime_Min,
            cd.CD_OptimumProductionTime AS ProductionTime_Optimum,
            cd.CD_MaxProductionTime AS ProductionTime_Max,
            cd.CD_MinAmount AS MinOrderQty,
            cd.CD_MaxAmount AS MaxOrderQty,
            cd.CD_Currency AS Currency,
            cd.CD_Price AS UnitPrice
        FROM dbo.CtiDelivery cd
        LEFT JOIN CDN.Towary t ON cd.CD_TwrId = t.Twr_TwrId
        LEFT JOIN CDN.Kontrahenci k ON cd.CD_KntId = k.Knt_KntId
        WHERE 1=1 {product_filter}
        ORDER BY cd.CD_DefaultProvider DESC, t.Twr_Kod
        """

        df = self.execute_query(query, params=params if params else None, query_name="get_product_delivery_info")

        if use_cache and not df.empty:
            self._set_cache(cache_key, df)

        return df

    def get_product_lead_times(self, product_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetch product lead times from CtiTwrCzasy table.
        Contains delivery and production times at product level.
        """
        cache_key = f"lead_times_{product_id or 'all'}"

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        product_filter = ""
        params = {}
        if product_id is not None:
            product_filter = "AND crc.CRC_TwrId = :product_id"
            params["product_id"] = product_id

        query = f"""
        SELECT
            crc.CRC_TwrId AS ProductId,
            t.Twr_Kod AS ProductCode,
            t.Twr_Nazwa AS ProductName,
            crc.CRC_CzasMinMin AS LeadTime_Min,
            crc.CRC_CzasOPTIMin AS LeadTime_Optimum,
            crc.CRC_CzasMAXMin AS LeadTime_Max,
            crc.CRC_CzasMinTyp AS LeadTime_Type,
            crc.CRC_KosztMin AS LeadCost_Min,
            crc.CRC_KosztOPTI AS LeadCost_Optimum,
            crc.CRC_KosztMAX AS LeadCost_Max,
            crc.CRC_CzasMinMinP AS ProdTime_Min,
            crc.CRC_CzasOPTIMinP AS ProdTime_Optimum,
            crc.CRC_CzasMAXMinP AS ProdTime_Max,
            crc.CRC_CzasMinTypP AS ProdTime_Type,
            crc.CRC_KosztMinP AS ProdCost_Min,
            crc.CRC_KosztOPTIP AS ProdCost_Optimum,
            crc.CRC_KosztMAXP AS ProdCost_Max,
            crc.CRC_OpisOPTI AS Description
        FROM dbo.CtiTwrCzasy crc
        LEFT JOIN CDN.Towary t ON crc.CRC_TwrId = t.Twr_TwrId
        WHERE crc.CRC_TwrId IS NOT NULL {product_filter}
        ORDER BY t.Twr_Kod
        """

        df = self.execute_query(query, params=params if params else None, query_name="get_product_lead_times")

        if not df.empty:
            time_type_map = {1: "hours", 2: "days", 3: "weeks"}
            if "LeadTime_Type" in df.columns:
                df["LeadTime_Unit"] = df["LeadTime_Type"].map(time_type_map).fillna("days")
            if "ProdTime_Type" in df.columns:
                df["ProdTime_Unit"] = df["ProdTime_Type"].map(time_type_map).fillna("days")

            if use_cache:
                self._set_cache(cache_key, df)

        return df
