"""
Database Consistency Tests.
Verifies that application queries return results consistent with direct SQL.

These tests require database connection and use real data.
"""

import pytest


@pytest.mark.integration
class TestBomConsistency:
    """Test BOM data consistency between app and direct SQL."""

    def test_bom_ingredient_count_matches_sql(self):
        """Verify get_bom_with_stock returns same count as direct SQL."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

        # Get a product with technology
        products = db.get_products_with_technology()
        if products.empty:
            pytest.skip("No products with technology found")

        product_id = products.iloc[0]["FinalProductId"]

        # Via application method
        bom_app = db.get_bom_with_stock(product_id)

        # Direct SQL count
        count_sql = """
            SELECT COUNT(*) as cnt
            FROM CtiTechnolNag n
            JOIN CtiTechnolElem e ON n.CTN_ID = e.CTE_CTNId
            WHERE n.CTN_TwrId = :product_id
              AND e.CTE_Typ IN (1, 2)
        """
        count_result = db.execute_query(count_sql, params={"product_id": product_id})

        assert len(bom_app) == count_result.iloc[0]["cnt"], (
            f"BOM count mismatch: app={len(bom_app)}, sql={count_result.iloc[0]['cnt']}"
        )

    def test_stock_sum_matches_twrzasoby(self):
        """Verify CurrentStock in BOM matches TwrZasoby aggregation."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

        products = db.get_products_with_technology()
        if products.empty:
            pytest.skip("No products with technology found")

        product_id = products.iloc[0]["FinalProductId"]
        bom_app = db.get_bom_with_stock(product_id)

        if bom_app.empty:
            pytest.skip("BOM is empty")

        # For first ingredient, verify stock
        ingredient_code = bom_app.iloc[0]["IngredientCode"]
        app_stock = bom_app.iloc[0]["CurrentStock"]

        # Direct SQL
        stock_sql = """
            SELECT ISNULL(SUM(z.TwZ_Ilosc), 0) as StockSum
            FROM CDN.Towary t
            LEFT JOIN CDN.TwrZasoby z ON t.Twr_TwrId = z.TwZ_TwrId
            WHERE t.Twr_Kod = :ingredient_code
        """
        stock_result = db.execute_query(stock_sql, params={"ingredient_code": ingredient_code})

        sql_stock = stock_result.iloc[0]["StockSum"]

        assert abs(app_stock - sql_stock) < 0.01, (
            f"Stock mismatch for {ingredient_code}: app={app_stock}, sql={sql_stock}"
        )


@pytest.mark.integration
class TestHistoricalDataConsistency:
    """Test historical data aggregation consistency."""

    def test_weekly_aggregation_sum_matches_sql(self):
        """Verify weekly quantity sum matches direct SQL."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

        # Get recent data (last 30 days)
        from datetime import datetime, timedelta

        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        historical = db.get_historical_data(date_from=date_from, date_to=date_to)

        if historical.empty:
            pytest.skip("No historical data in date range")

        app_total = historical["Quantity"].sum()

        # Direct SQL
        total_sql = """
            SELECT SUM(e.CZE_Ilosc) as TotalQty
            FROM CtiZlecenieElem e
            JOIN CtiZlecenieNag n ON e.CZE_CZNId = n.CZN_ID
            JOIN CDN.Towary t ON e.CZE_TwrId = t.Twr_TwrId
            WHERE n.CZN_DataRealizacji BETWEEN :date_from AND :date_to
              AND e.CZE_Typ IN (1, 2)
              AND t.Twr_Typ != 2
        """
        result = db.execute_query(total_sql, params={"date_from": date_from, "date_to": date_to})

        sql_total = result.iloc[0]["TotalQty"] or 0

        # Allow 1% tolerance for rounding
        tolerance = abs(app_total * 0.01)
        assert abs(app_total - sql_total) <= tolerance, f"Total mismatch: app={app_total}, sql={sql_total}"


@pytest.mark.integration
class TestWarehouseConsistency:
    """Test warehouse data consistency."""

    def test_warehouse_stock_sum_matches_sql(self):
        """Verify warehouse total stock matches TwrZasoby."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

        warehouses = db.get_warehouses(only_with_stock=True)

        if warehouses.empty:
            pytest.skip("No warehouses with stock")

        for _, wh in warehouses.head(3).iterrows():
            mag_id = wh["MagId"]
            app_total = wh["TotalStock"]

            # Direct SQL
            sql = """
                SELECT ISNULL(SUM(TwZ_Ilosc), 0) as Total
                FROM CDN.TwrZasoby
                WHERE TwZ_MagId = :mag_id
            """
            result = db.execute_query(sql, params={"mag_id": mag_id})
            sql_total = result.iloc[0]["Total"]

            assert abs(app_total - sql_total) < 0.01, (
                f"Warehouse {wh['Symbol']} stock mismatch: app={app_total}, sql={sql_total}"
            )
