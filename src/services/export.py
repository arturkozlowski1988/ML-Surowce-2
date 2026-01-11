"""
Export Module - Data Export and BI Reporting
AI Supply Assistant - Phase 3

Provides export functionality for:
- Forecasts to CSV
- Shortage reports
- KPI dashboards
"""

import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger("ExportModule")


class DataExporter:
    """
    Data export utilities for BI and reporting.

    Usage:
        exporter = DataExporter(output_dir="exports")
        path = exporter.export_forecasts(df_forecast)
    """

    def __init__(self, output_dir: str = "exports"):
        """
        Initialize the exporter.

        Args:
            output_dir: Directory for export files (default: "exports")
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_to_csv(self, df: pd.DataFrame, filename: str, include_timestamp: bool = True) -> str:
        """
        Exports DataFrame to CSV file.

        Args:
            df: DataFrame to export
            filename: Base filename (without extension)
            include_timestamp: If True, adds timestamp to filename

        Returns:
            Full path to exported file
        """
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            full_filename = f"{filename}_{timestamp}.csv"
        else:
            full_filename = f"{filename}.csv"

        filepath = os.path.join(self.output_dir, full_filename)

        df.to_csv(filepath, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compatibility

        logger.info(f"Exported {len(df)} rows to {filepath}")

        return filepath

    def export_forecasts(self, forecast_df: pd.DataFrame, product_map: dict[int, str] = None) -> str:
        """
        Exports forecast data with optional product name enrichment.

        Args:
            forecast_df: DataFrame with columns: TowarId, Date, Predicted_Qty, Model
            product_map: Optional mapping of TowarId to product names

        Returns:
            Path to exported CSV
        """
        df = forecast_df.copy()

        if product_map:
            df["ProductName"] = df["TowarId"].map(product_map)
            cols = ["TowarId", "ProductName", "Date", "Predicted_Qty", "Model"]
            df = df[cols]

        return self.export_to_csv(df, "forecast_export")

    def export_shortages(self, shortage_df: pd.DataFrame, target_quantity: float = None) -> str:
        """
        Exports shortage analysis data.

        Args:
            shortage_df: DataFrame with shortage information
            target_quantity: Optional target quantity for context

        Returns:
            Path to exported CSV
        """
        df = shortage_df.copy()

        if target_quantity:
            df["TargetQuantity"] = target_quantity

        df["ExportDate"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        return self.export_to_csv(df, "shortage_export")

    def export_alerts(self, alerts_df: pd.DataFrame) -> str:
        """
        Exports alert data for external processing.

        Args:
            alerts_df: DataFrame from SmartAlerts.get_critical_shortages()

        Returns:
            Path to exported CSV
        """
        df = alerts_df.copy()
        df["ExportDate"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        return self.export_to_csv(df, "alerts_export")

    def export_vendor_stats(self, vendor_df: pd.DataFrame) -> str:
        """
        Exports vendor delivery statistics.

        Args:
            vendor_df: DataFrame from get_vendor_delivery_stats()

        Returns:
            Path to exported CSV
        """
        df = vendor_df.copy()
        df["ExportDate"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        return self.export_to_csv(df, "vendor_stats_export")

    def generate_kpi_report(self, db_connector, warehouse_ids: list[int] = None) -> dict:
        """
        Generates KPI summary for management reporting.

        Args:
            db_connector: DatabaseConnector instance
            warehouse_ids: Optional warehouse filter

        Returns:
            Dictionary with KPI metrics
        """
        from src.services.alerts import SmartAlerts

        alerts = SmartAlerts(db_connector)
        summary = alerts.get_shortage_summary()

        # Get additional stats
        df_stock = db_connector.get_current_stock(warehouse_ids=warehouse_ids)
        total_stock_value = df_stock["StockLevel"].sum() if not df_stock.empty else 0

        df_hist = db_connector.get_historical_data()
        avg_weekly_consumption = df_hist["Quantity"].mean() if not df_hist.empty else 0

        kpi = {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_products": len(df_stock),
            "total_stock_qty": total_stock_value,
            "avg_weekly_consumption": round(avg_weekly_consumption, 2),
            "critical_items": summary.get("critical_count", 0),
            "low_stock_items": summary.get("low_count", 0),
            "ok_items": summary.get("ok_count", 0),
            "alert_rate_percent": round(
                (summary.get("critical_count", 0) + summary.get("low_count", 0))
                / max(summary.get("total_items", 1), 1)
                * 100,
                1,
            ),
        }

        logger.info(f"KPI Report generated: {kpi}")

        return kpi

    def export_kpi_report(self, db_connector, warehouse_ids: list[int] = None) -> str:
        """
        Exports KPI report to CSV.

        Returns:
            Path to exported CSV
        """
        kpi = self.generate_kpi_report(db_connector, warehouse_ids)
        df = pd.DataFrame([kpi])

        return self.export_to_csv(df, "kpi_report")
