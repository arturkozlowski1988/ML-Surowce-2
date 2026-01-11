"""
Smart Alerts - Intelligent Shortage Detection and Notification
AI Supply Assistant - Phase 2

This module provides real-time alerts for critical inventory shortages:
- Formula: Stan Obecny - Rezerwacje + W Drodze < Minimum Logistyczne
- AI-powered explanation of shortage causes
- Dashboard-ready data formatting
"""

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger("SmartAlerts")


class SmartAlerts:
    """
    Intelligent alerting system for inventory management.

    Usage:
        alerts = SmartAlerts(db_connector)
        critical = alerts.get_critical_shortages()
        explanations = alerts.generate_ai_explanations(critical, llm_client)
    """

    def __init__(self, db_connector, minimum_stock_days: int = 14):
        """
        Initialize Smart Alerts.

        Args:
            db_connector: DatabaseConnector instance
            minimum_stock_days: Days of stock to maintain as minimum (default: 14)
        """
        self.db = db_connector
        self.minimum_stock_days = minimum_stock_days

    def get_critical_shortages(self, warehouse_ids: list[int] = None, include_all: bool = False) -> pd.DataFrame:
        """
        Identifies items with critical stock levels.

        Formula: Current Stock < Average Weekly Consumption * (minimum_stock_days / 7)

        Args:
            warehouse_ids: Optional filter by warehouses
            include_all: If True, includes items without recent usage

        Returns:
            DataFrame with columns:
            - Code, Name, CurrentStock
            - AvgWeeklyUsage, DaysOfStock
            - Status (KRYTYCZNY, NISKI, OK)
            - Priority (1=highest)
        """
        logger.info("Analyzing critical shortages...")

        # Get current stock
        df_stock = self.db.get_current_stock(warehouse_ids=warehouse_ids)

        if df_stock.empty:
            return pd.DataFrame()

        # Get historical usage for average calculation
        # Look back 12 weeks for stable average
        df_hist = self.db.get_historical_data()

        if df_hist.empty:
            logger.warning("No historical data available for shortage analysis")
            return df_stock.assign(AvgWeeklyUsage=0, DaysOfStock=float("inf"), Status="BRAK DANYCH", Priority=99)

        # Calculate average weekly usage per product
        usage_stats = df_hist.groupby("TowarId").agg({"Quantity": ["mean", "sum", "count"]}).reset_index()
        usage_stats.columns = ["TowarId", "AvgWeeklyUsage", "TotalUsage", "WeeksWithUsage"]

        # Merge with current stock
        df = df_stock.merge(usage_stats, on="TowarId", how="left")

        # Fill missing usage with 0
        df["AvgWeeklyUsage"] = df["AvgWeeklyUsage"].fillna(0)
        df["TotalUsage"] = df["TotalUsage"].fillna(0)
        df["WeeksWithUsage"] = df["WeeksWithUsage"].fillna(0)

        # Calculate days of stock remaining
        df["DaysOfStock"] = df.apply(
            lambda row: (row["StockLevel"] / (row["AvgWeeklyUsage"] / 7))
            if row["AvgWeeklyUsage"] > 0
            else float("inf"),
            axis=1,
        )

        # Determine status based on days of stock
        minimum_days = self.minimum_stock_days

        def get_status(days):
            if days == float("inf"):
                return "BRAK UŻYCIA"
            elif days < minimum_days * 0.5:  # Less than 50% of minimum
                return "KRYTYCZNY"
            elif days < minimum_days:  # Less than minimum
                return "NISKI"
            else:
                return "OK"

        df["Status"] = df["DaysOfStock"].apply(get_status)

        # Assign priority (lower = more urgent)
        def get_priority(row):
            if row["Status"] == "KRYTYCZNY":
                return 1
            elif row["Status"] == "NISKI":
                return 2
            elif row["Status"] == "BRAK UŻYCIA":
                return 4
            else:
                return 3

        df["Priority"] = df.apply(get_priority, axis=1)

        # Filter out OK items unless include_all
        if not include_all:
            df = df[df["Status"].isin(["KRYTYCZNY", "NISKI"])]

        # Sort by priority
        df = df.sort_values(["Priority", "DaysOfStock"])

        # Format columns for display
        df["DaysOfStock"] = df["DaysOfStock"].apply(lambda x: f"{x:.0f}" if x != float("inf") else "∞")
        df["AvgWeeklyUsage"] = df["AvgWeeklyUsage"].round(2)

        logger.info(f"Found {len(df)} items with shortage alerts")

        return df[["Code", "Name", "StockLevel", "AvgWeeklyUsage", "DaysOfStock", "Status", "Priority"]]

    def generate_ai_context(self, shortages_df: pd.DataFrame) -> str:
        """
        Generates context string for AI explanation of shortages.

        Args:
            shortages_df: DataFrame from get_critical_shortages()

        Returns:
            Formatted string for LLM prompt
        """
        if shortages_df.empty:
            return "Brak krytycznych braków magazynowych."

        lines = [
            "## Analiza Krytycznych Braków Magazynowych",
            "",
            f"**Data analizy:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Liczba alertów:** {len(shortages_df)}",
            "",
            "### Lista Braków (wg priorytetu)",
            "",
            "| Kod | Nazwa | Stan | Śr. Tyg. | Dni Zapasu | Status |",
            "|-----|-------|------|----------|------------|--------|",
        ]

        for _, row in shortages_df.head(15).iterrows():
            lines.append(
                f"| {row['Code']} | {row['Name'][:30]} | "
                f"{row['StockLevel']:.1f} | {row['AvgWeeklyUsage']} | "
                f"{row['DaysOfStock']} | **{row['Status']}** |"
            )

        if len(shortages_df) > 15:
            lines.append(f"\n*... i {len(shortages_df) - 15} więcej*")

        lines.extend(
            [
                "",
                "### Proszę o:",
                "1. Wyjaśnienie możliwych przyczyn niskiego stanu",
                "2. Rekomendacje działań zakupowych",
                "3. Ocenę pilności poszczególnych pozycji",
            ]
        )

        return "\n".join(lines)

    def get_shortage_summary(self) -> dict:
        """
        Returns summary statistics for dashboard display.
        """
        df = self.get_critical_shortages(include_all=True)

        if df.empty:
            return {"total_items": 0, "critical_count": 0, "low_count": 0, "ok_count": 0, "no_usage_count": 0}

        return {
            "total_items": len(df),
            "critical_count": len(df[df["Status"] == "KRYTYCZNY"]),
            "low_count": len(df[df["Status"] == "NISKI"]),
            "ok_count": len(df[df["Status"] == "OK"]),
            "no_usage_count": len(df[df["Status"] == "BRAK UŻYCIA"]),
        }
