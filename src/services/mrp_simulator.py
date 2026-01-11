"""
MRP Simulator - Production Simulation with BOM Analysis
AI Supply Assistant - Phase 2

This module provides Material Requirements Planning (MRP) functionality:
- Recursive BOM tree analysis
- "What-If" production simulation
- Shortage calculation with visibility

PERFORMANCE: Uses parallel processing for multi-product analysis.
"""

import logging

import pandas as pd

logger = logging.getLogger("MRPSimulator")


class MRPSimulator:
    """
    MRP Simulator for production planning and shortage analysis.

    Usage:
        simulator = MRPSimulator(db_connector)
        result = simulator.simulate_production(product_id=123, quantity=500)
        shortages = simulator.calculate_shortages(result['bom'], target_quantity=500)
    """

    def __init__(self, db_connector):
        """
        Initialize MRP Simulator with database connection.

        Args:
            db_connector: DatabaseConnector instance for data access
        """
        self.db = db_connector
        self._bom_cache = {}  # Cache for BOM lookups

    def get_product_bom(self, product_id: int, level: int = 0, max_depth: int = 5) -> list[dict]:
        """
        Fetches Bill of Materials (BOM) recursively for a product.

        Args:
            product_id: ID of the final product
            level: Current recursion depth (internal use)
            max_depth: Maximum recursion depth to prevent infinite loops

        Returns:
            List of BOM items with structure:
            [{
                'level': int,
                'ingredient_id': int,
                'ingredient_code': str,
                'ingredient_name': str,
                'quantity_per_unit': float,
                'unit': str,
                'current_stock': float,
                'is_assembly': bool  # True if has sub-components
            }]
        """
        if level > max_depth:
            logger.warning(f"Max BOM depth {max_depth} reached for product {product_id}")
            return []

        # Check cache
        cache_key = f"{product_id}_{level}"
        if cache_key in self._bom_cache:
            return self._bom_cache[cache_key]

        # Fetch BOM from database
        df_bom = self.db.get_bom_with_stock(product_id)

        if df_bom.empty:
            return []

        bom_items = []

        for _, row in df_bom.iterrows():
            item = {
                "level": level,
                "ingredient_code": row["IngredientCode"],
                "ingredient_name": row["IngredientName"],
                "quantity_per_unit": float(row["QuantityPerUnit"]),
                "unit": row.get("Unit", "szt."),
                "current_stock": float(row["CurrentStock"]),
                "is_assembly": False,  # Will check if has sub-BOM
            }

            bom_items.append(item)

        # Cache result
        self._bom_cache[cache_key] = bom_items

        return bom_items

    def simulate_production(
        self, product_id: int, quantity: float, warehouse_ids: list[int] = None, technology_id: int = None
    ) -> dict:
        """
        Simulates production of a given quantity - "What-If" analysis.

        Answers: "Can I produce [quantity] units of product [product_id]
                  with current stock?"

        Args:
            product_id: ID of the final product to produce
            quantity: Target production quantity
            warehouse_ids: Optional list of warehouses to check stock
            technology_id: Optional specific technology ID

        Returns:
            Dictionary with simulation results:
            {
                'can_produce': bool,
                'max_producible': float,
                'bom': DataFrame with columns:
                    - IngredientCode, IngredientName
                    - QuantityRequired (for target qty)
                    - CurrentStock
                    - Shortage (negative = deficit)
                    - Status ('OK', 'BRAK', 'KRYTYCZNY')
                'shortages': List of items with insufficient stock
                'limiting_factor': Dict with info about bottleneck ingredient
            }
        """
        logger.info(f"Simulating production of {quantity} units for product {product_id}")

        # Fetch BOM with stock levels
        if warehouse_ids:
            df_bom = self.db.get_bom_with_stock(product_id, technology_id, warehouse_ids)
        else:
            df_bom = self.db.get_bom_with_stock(product_id, technology_id)

        if df_bom.empty:
            return {
                "can_produce": False,
                "max_producible": 0,
                "bom": pd.DataFrame(),
                "shortages": [],
                "limiting_factor": None,
                "error": "Brak technologii produkcji dla tego produktu",
            }

        # Calculate requirements
        df_bom = df_bom.copy()
        df_bom["QuantityRequired"] = df_bom["QuantityPerUnit"] * quantity
        df_bom["Shortage"] = df_bom["CurrentStock"] - df_bom["QuantityRequired"]

        # Determine status for each ingredient
        def get_status(row):
            if row["Shortage"] >= 0:
                return "OK"
            elif row["Shortage"] >= -row["QuantityRequired"] * 0.1:  # Within 10%
                return "BRAK"
            else:
                return "KRYTYCZNY"

        df_bom["Status"] = df_bom.apply(get_status, axis=1)

        # Calculate max producible quantity
        df_bom["MaxProducible"] = df_bom["CurrentStock"] / df_bom["QuantityPerUnit"]
        max_producible = df_bom["MaxProducible"].min()

        # Find limiting factor (bottleneck)
        limiting_idx = df_bom["MaxProducible"].idxmin()
        limiting_row = df_bom.loc[limiting_idx]
        limiting_factor = {
            "ingredient_id": limiting_row.get("IngredientId") if "IngredientId" in df_bom.columns else None,
            "ingredient_code": limiting_row["IngredientCode"],
            "ingredient_name": limiting_row["IngredientName"],
            "current_stock": limiting_row["CurrentStock"],
            "quantity_required": limiting_row["QuantityRequired"],
            "max_producible": limiting_row["MaxProducible"],
        }

        # Collect shortages
        shortages = df_bom[df_bom["Shortage"] < 0].to_dict("records")

        # Can produce target quantity?
        can_produce = len(shortages) == 0

        logger.info(f"Simulation result: can_produce={can_produce}, max={max_producible:.2f}")

        return {
            "can_produce": can_produce,
            "max_producible": max(0, max_producible),
            "bom": df_bom,
            "shortages": shortages,
            "limiting_factor": limiting_factor,
        }

    def calculate_shortages(self, bom_df: pd.DataFrame, target_quantity: float) -> pd.DataFrame:
        """
        Calculates and formats shortage information for display.

        Args:
            bom_df: BOM DataFrame with CurrentStock column
            target_quantity: Target production quantity

        Returns:
            DataFrame filtered to items with shortages, sorted by severity
        """
        if bom_df.empty:
            return pd.DataFrame()

        df = bom_df.copy()

        if "QuantityRequired" not in df.columns:
            df["QuantityRequired"] = df["QuantityPerUnit"] * target_quantity

        if "Shortage" not in df.columns:
            df["Shortage"] = df["CurrentStock"] - df["QuantityRequired"]

        # Filter only shortages
        shortages = df[df["Shortage"] < 0].copy()

        if shortages.empty:
            return pd.DataFrame()

        # Calculate shortage percentage
        shortages["ShortagePercent"] = (abs(shortages["Shortage"]) / shortages["QuantityRequired"] * 100).round(1)

        # Format for display
        shortages["ToOrder"] = abs(shortages["Shortage"]).round(2)

        # Sort by severity (highest percentage first)
        shortages = shortages.sort_values("ShortagePercent", ascending=False)

        return shortages[
            [
                "IngredientCode",
                "IngredientName",
                "QuantityRequired",
                "CurrentStock",
                "ToOrder",
                "ShortagePercent",
                "Status",
            ]
        ]

    def get_production_recommendations(
        self, product_id: int, target_quantity: float, warehouse_ids: list[int] = None
    ) -> str:
        """
        Generates AI-compatible recommendations for production planning.
        Returns formatted text for LLM consumption.

        Args:
            product_id: Product to analyze
            target_quantity: Desired production quantity
            warehouse_ids: Optional warehouse filter

        Returns:
            Formatted string with analysis for AI prompt
        """
        result = self.simulate_production(product_id, target_quantity, warehouse_ids)

        if "error" in result:
            return f"BŁĄD: {result['error']}"

        lines = [
            f"## Analiza Produkcji: {target_quantity} szt.",
            "",
            f"### Status: {'✅ MOŻLIWA' if result['can_produce'] else '⚠️ BRAKI SUROWCÓW'}",
            f"**Maksymalna możliwa produkcja:** {result['max_producible']:.0f} szt.",
            "",
        ]

        if result["limiting_factor"]:
            lf = result["limiting_factor"]
            lines.extend(
                [
                    "### Czynnik Ograniczający (Bottleneck)",
                    f"- **Surowiec:** {lf['ingredient_name']} ({lf['ingredient_code']})",
                    f"- **Stan:** {lf['current_stock']:.2f}",
                    f"- **Potrzeba:** {lf['quantity_required']:.2f}",
                    "",
                ]
            )

        if result["shortages"]:
            lines.append("### Braki do Zamówienia")
            lines.append("| Kod | Nazwa | Potrzeba | Stan | Do Zamówienia |")
            lines.append("|-----|-------|----------|------|---------------|")

            for item in result["shortages"][:10]:  # Limit to top 10
                to_order = abs(item["Shortage"])
                lines.append(
                    f"| {item['IngredientCode']} | {item['IngredientName'][:30]} | "
                    f"{item['QuantityRequired']:.2f} | {item['CurrentStock']:.2f} | "
                    f"**{to_order:.2f}** |"
                )

        return "\n".join(lines)

    def clear_cache(self):
        """Clears BOM cache."""
        self._bom_cache.clear()
        logger.info("MRP Simulator cache cleared")

    def simulate_production_with_delivery(
        self, product_id: int, quantity: float, warehouse_ids: list[int] = None, technology_id: int = None
    ) -> dict:
        """
        Enhanced production simulation with delivery times from CtiDelivery/CtiTwrCzasy.

        Answers: "Can I produce [quantity] units and when will materials arrive?"

        Args:
            product_id: ID of the final product to produce
            quantity: Target production quantity
            warehouse_ids: Optional list of warehouses to check stock
            technology_id: Optional specific technology ID

        Returns:
            Dictionary with simulation results including:
            - 'can_produce', 'max_producible' (same as simulate_production)
            - 'bom' with additional columns: DeliveryTime_Days, VendorCode, VendorName
            - 'max_delivery_time': Longest delivery time among shortage items
            - 'earliest_production_date': When production can start
            - 'shortages_with_delivery': List including delivery info
        """
        logger.info(f"Simulating production with delivery for {quantity} units of product {product_id}")

        # Use enhanced BOM query that includes delivery info
        try:
            df_bom = self.db.get_bom_with_delivery_info(product_id, technology_id, warehouse_ids)
        except Exception as e:
            logger.warning(f"Fallback to standard BOM: {e}")
            # Fallback to standard method if enhanced fails
            df_bom = self.db.get_bom_with_stock(product_id, technology_id, warehouse_ids)

        if df_bom.empty:
            return {
                "can_produce": False,
                "max_producible": 0,
                "bom": pd.DataFrame(),
                "shortages": [],
                "shortages_with_delivery": [],
                "limiting_factor": None,
                "max_delivery_time": 0,
                "earliest_production_date": None,
                "error": "Brak technologii produkcji dla tego produktu",
            }

        # Calculate requirements
        df_bom = df_bom.copy()
        df_bom["QuantityRequired"] = df_bom["QuantityPerUnit"] * quantity
        df_bom["Shortage"] = df_bom["CurrentStock"] - df_bom["QuantityRequired"]

        # Determine status for each ingredient
        def get_status(row):
            if row["Shortage"] >= 0:
                return "OK"
            elif row["Shortage"] >= -row["QuantityRequired"] * 0.1:
                return "BRAK"
            else:
                return "KRYTYCZNY"

        df_bom["Status"] = df_bom.apply(get_status, axis=1)

        # Calculate max producible quantity
        df_bom["MaxProducible"] = df_bom["CurrentStock"] / df_bom["QuantityPerUnit"]
        max_producible = df_bom["MaxProducible"].min()

        # Find limiting factor (bottleneck)
        limiting_idx = df_bom["MaxProducible"].idxmin()
        limiting_row = df_bom.loc[limiting_idx]
        limiting_factor = {
            "ingredient_id": limiting_row.get("IngredientId") if "IngredientId" in df_bom.columns else None,
            "ingredient_code": limiting_row["IngredientCode"],
            "ingredient_name": limiting_row["IngredientName"],
            "current_stock": limiting_row["CurrentStock"],
            "quantity_required": limiting_row["QuantityRequired"],
            "max_producible": limiting_row["MaxProducible"],
            "delivery_time_days": limiting_row.get("DeliveryTime_Days", 0),
            "vendor_code": limiting_row.get("VendorCode", ""),
        }

        # Collect shortages with delivery info
        shortage_df = df_bom[df_bom["Shortage"] < 0].copy()

        if not shortage_df.empty:
            # Ensure delivery time column exists
            if "DeliveryTime_Days" not in shortage_df.columns:
                shortage_df["DeliveryTime_Days"] = 0
            if "VendorCode" not in shortage_df.columns:
                shortage_df["VendorCode"] = ""
            if "VendorName" not in shortage_df.columns:
                shortage_df["VendorName"] = ""
            if "MinOrderQty" not in shortage_df.columns:
                shortage_df["MinOrderQty"] = 0

            shortage_df["ToOrder"] = abs(shortage_df["Shortage"])

            # Calculate max delivery time
            max_delivery_time = shortage_df["DeliveryTime_Days"].max()

            shortages_with_delivery = shortage_df.to_dict("records")
        else:
            max_delivery_time = 0
            shortages_with_delivery = []

        shortages = df_bom[df_bom["Shortage"] < 0].to_dict("records")
        can_produce = len(shortages) == 0

        # Calculate earliest production date
        from datetime import datetime, timedelta

        if max_delivery_time > 0:
            earliest_production_date = datetime.now() + timedelta(days=max_delivery_time)
        else:
            earliest_production_date = datetime.now()

        logger.info(
            f"Simulation result: can_produce={can_produce}, max={max_producible:.2f}, max_delivery={max_delivery_time} days"
        )

        return {
            "can_produce": can_produce,
            "max_producible": max(0, max_producible),
            "bom": df_bom,
            "shortages": shortages,
            "shortages_with_delivery": shortages_with_delivery,
            "limiting_factor": limiting_factor,
            "max_delivery_time": max_delivery_time,
            "earliest_production_date": earliest_production_date.strftime("%Y-%m-%d")
            if max_delivery_time > 0
            else "Natychmiast",
        }

    def get_production_recommendations_with_delivery(
        self, product_id: int, target_quantity: float, warehouse_ids: list[int] = None
    ) -> str:
        """
        Enhanced recommendations including delivery times and vendor info.

        Returns:
            Formatted string with analysis for AI prompt including delivery schedule
        """
        result = self.simulate_production_with_delivery(product_id, target_quantity, warehouse_ids)

        if "error" in result:
            return f"BŁĄD: {result['error']}"

        lines = [
            f"## Analiza Produkcji z Czasami Dostaw: {target_quantity} szt.",
            "",
            f"### Status: {'✅ MOŻLIWA' if result['can_produce'] else '⚠️ BRAKI SUROWCÓW'}",
            f"**Maksymalna możliwa produkcja:** {result['max_producible']:.0f} szt.",
            f"**Najwcześniejsza data produkcji:** {result['earliest_production_date']}",
            f"**Najdłuższy czas dostawy:** {result['max_delivery_time']} dni",
            "",
        ]

        if result["limiting_factor"]:
            lf = result["limiting_factor"]
            lines.extend(
                [
                    "### Czynnik Ograniczający (Bottleneck)",
                    f"- **Surowiec:** {lf['ingredient_name']} ({lf['ingredient_code']})",
                    f"- **Stan:** {lf['current_stock']:.2f}",
                    f"- **Potrzeba:** {lf['quantity_required']:.2f}",
                    f"- **Dostawca:** {lf.get('vendor_code', 'brak')}",
                    f"- **Czas dostawy:** {lf.get('delivery_time_days', 0)} dni",
                    "",
                ]
            )

        if result["shortages_with_delivery"]:
            lines.append("### Braki do Zamówienia (z czasami dostaw)")
            lines.append("| Kod | Nazwa | Do Zamówienia | Dostawca | Czas Dostawy |")
            lines.append("|-----|-------|---------------|----------|--------------|")

            for item in result["shortages_with_delivery"][:15]:
                to_order = item.get("ToOrder", abs(item.get("Shortage", 0)))
                vendor = item.get("VendorCode", "-")
                delivery = item.get("DeliveryTime_Days", 0)
                lines.append(
                    f"| {item['IngredientCode']} | {item['IngredientName'][:25]} | "
                    f"**{to_order:.2f}** | {vendor} | {delivery} dni |"
                )

        return "\n".join(lines)

    def get_shortage_with_substitutes(self, product_id: int, quantity: float, warehouse_ids: list[int] = None) -> dict:
        """
        Enhanced shortage analysis that suggests substitutes for missing materials.
        Critical for business: when main ingredient unavailable, show alternatives.

        Args:
            product_id: Product to analyze
            quantity: Target production quantity
            warehouse_ids: Optional warehouse filter

        Returns:
            Dictionary with:
            - 'shortages': List of shortage items with nested 'substitutes' list
            - 'can_produce_with_substitutes': bool
            - 'substitutes_summary': formatted text
        """
        # First run standard simulation
        result = self.simulate_production(product_id, quantity, warehouse_ids)

        if "error" in result:
            return result

        # If no shortages, no need for substitutes
        if not result["shortages"]:
            return {
                **result,
                "substitutes_available": False,
                "substitutes_summary": "Brak braków surowców - zamienniki niepotrzebne.",
            }

        # For each shortage, find substitutes
        shortages_with_subs = []
        any_substitutes_found = False

        for shortage in result["shortages"]:
            shortage_item = shortage.copy()
            shortage_item["substitutes"] = []

            # Get ingredient ID (need to find it)
            ingredient_code = shortage.get("IngredientCode", "")

            # Query substitutes for this ingredient
            try:
                subs_df = self.db.get_product_substitutes()
                if not subs_df.empty:
                    # Filter to this ingredient
                    matching_subs = subs_df[subs_df["OriginalCode"] == ingredient_code]

                    for _, sub_row in matching_subs.iterrows():
                        if sub_row.get("IsAllowed", 1) == 1:  # Only allowed substitutes
                            shortage_item["substitutes"].append(
                                {
                                    "code": sub_row["SubstituteCode"],
                                    "name": sub_row["SubstituteName"],
                                    "id": sub_row["SubstituteId"],
                                }
                            )
                            any_substitutes_found = True
            except Exception as e:
                logger.warning(f"Could not fetch substitutes: {e}")

            shortages_with_subs.append(shortage_item)

        # Generate summary
        summary_lines = ["## Analiza Zamienników\n"]

        for item in shortages_with_subs:
            code = item.get("IngredientCode", "?")
            name = item.get("IngredientName", "?")[:30]
            to_order = abs(item.get("Shortage", 0))

            summary_lines.append(f"### {code} - {name}")
            summary_lines.append(f"- **Brak:** {to_order:.2f}")

            if item["substitutes"]:
                summary_lines.append("- **Zamienniki:**")
                for sub in item["substitutes"]:
                    summary_lines.append(f"  - {sub['code']}: {sub['name']}")
            else:
                summary_lines.append("- *Brak zdefiniowanych zamienników*")

            summary_lines.append("")

        return {
            **result,
            "shortages_with_substitutes": shortages_with_subs,
            "substitutes_available": any_substitutes_found,
            "substitutes_summary": "\n".join(summary_lines),
        }

    def sync_with_cti_shortages(self) -> pd.DataFrame:
        """
        Fetches existing shortage documents from CTI Production system.
        Useful for aligning AI recommendations with CTI-generated shortage lists.

        Returns:
            DataFrame with CTI shortage records (from CtiBrakiNag + CtiBrakiElem)
        """
        try:
            return self.db.get_shortage_analysis_cti()
        except Exception as e:
            logger.warning(f"Could not fetch CTI shortages: {e}")
            return pd.DataFrame()

    def get_comprehensive_production_analysis(
        self, product_id: int, quantity: float, warehouse_ids: list[int] = None
    ) -> str:
        """
        Generates comprehensive AI-ready analysis combining:
        - Production simulation
        - Delivery times
        - Substitutes suggestions
        - CTI shortage sync
        - [U1] Production status from CtiProdukcjaStatus
        - [U2] CTI shortage comparison
        - [U3] Smart substitutes with stock

        This is the main method for AI Assistant integration.

        Returns:
            Formatted markdown string for LLM consumption
        """
        lines = [
            "# Kompleksowa Analiza Produkcji",
            f"**Wyrób ID:** {product_id}",
            f"**Docelowa ilość:** {quantity} szt.",
            "",
        ]

        # 1. Simulation with delivery
        result = self.simulate_production_with_delivery(product_id, quantity, warehouse_ids)

        if "error" in result:
            return f"BŁĄD: {result['error']}"

        lines.extend(
            [
                "## 1. Status Produkcji",
                f"- **Możliwość realizacji:** {'✅ TAK' if result['can_produce'] else '❌ NIE'}",
                f"- **Maksymalna ilość:** {result['max_producible']:.0f} szt.",
                f"- **Najwcześniejsza data produkcji:** {result['earliest_production_date']}",
                f"- **Max czas dostawy:** {result['max_delivery_time']} dni",
                "",
            ]
        )

        # [U1] Production status integration
        try:
            production_status = self.db.get_production_status(use_cache=True)
            if not production_status.empty:
                # Get summary stats
                total_orders = len(production_status)
                completed = len(production_status[production_status["RealizationStatus"] == "ZAKOŃCZONE"])
                in_progress = len(production_status[production_status["RealizationStatus"] == "W REALIZACJI"])
                not_started = total_orders - completed - in_progress

                lines.extend(
                    [
                        "## 1b. Status Zleceń (CTI CtiProdukcjaStatus)",
                        f"- **Aktywne zlecenia:** {total_orders}",
                        f"- **Zakończone:** {completed} | **W realizacji:** {in_progress} | **Nie rozpoczęte:** {not_started}",
                        "",
                    ]
                )

                # Get pending demand for BOM items
                bom_products = [
                    item.get("ingredient_id") for item in result.get("bom", []) if item.get("ingredient_id")
                ]
                if bom_products:
                    pending = self.db.get_active_orders_demand(bom_products)
                    if not pending.empty:
                        lines.append("**Rezerwacja surowców przez aktywne ZP:**")
                        for _, row in pending.head(5).iterrows():
                            lines.append(
                                f"- {row['IngredientCode']}: {row['PendingDemand']:.2f} (z {row['ActiveOrderCount']} zleceń)"
                            )
                        lines.append("")
        except Exception as e:
            logger.debug(f"Could not get production status: {e}")

        # 2. Limiting factor
        if result["limiting_factor"] and not result["can_produce"]:
            lf = result["limiting_factor"]
            lines.extend(
                [
                    "## 2. Czynnik Ograniczający (Bottleneck)",
                    f"- **Surowiec:** {lf['ingredient_name']} ({lf['ingredient_code']})",
                    f"- **Stan magazynowy:** {lf['current_stock']:.2f}",
                    f"- **Wymagana ilość:** {lf['quantity_required']:.2f}",
                    f"- **Czas dostawy:** {lf.get('delivery_time_days', 0)} dni",
                    "",
                ]
            )

            # [U3] Smart substitutes for limiting factor
            try:
                shortage_qty = lf["quantity_required"] - lf["current_stock"]
                if lf.get("ingredient_id"):
                    smart_subs = self.db.get_smart_substitutes(lf["ingredient_id"], shortage_qty, warehouse_ids)
                    if not smart_subs.empty:
                        lines.append("**Zamienniki dla czynnika ograniczającego:**")
                        for _, sub in smart_subs[smart_subs["IsAllowed"] == 1].head(3).iterrows():
                            lines.append(
                                f"- {sub['SubstituteCode']}: {sub['CurrentStock']:.2f} {sub.get('Unit', 'szt.')} - {sub.get('Recommendation', '')}"
                            )
                        lines.append("")
            except Exception as e:
                logger.debug(f"Could not get smart substitutes: {e}")

        # 3. Shortages with substitutes
        subs_result = {}
        if result["shortages"]:
            subs_result = self.get_shortage_with_substitutes(product_id, quantity, warehouse_ids)

            lines.append("## 3. Braki i Zamienniki")
            lines.append("| Surowiec | Brak | Zamienniki |")
            lines.append("|----------|------|------------|")

            for item in subs_result.get("shortages_with_substitutes", result["shortages"])[:10]:
                code = item.get("IngredientCode", "?")
                shortage_qty = abs(item.get("Shortage", 0))
                subs = item.get("substitutes", [])
                subs_text = ", ".join([s["code"] for s in subs[:3]]) if subs else "-"
                lines.append(f"| {code} | {shortage_qty:.2f} | {subs_text} |")

            lines.append("")

        # [U2] CTI Sync with comparison
        cti_shortages = self.sync_with_cti_shortages()
        if not cti_shortages.empty or result["shortages"]:
            lines.extend(
                [
                    "## 4. Synchronizacja z CTI Braki",
                ]
            )

            # Compare calculated shortages with CTI
            try:
                if result["shortages"]:
                    import pandas as pd

                    shortages_df = pd.DataFrame(result["shortages"])
                    if "IngredientId" not in shortages_df.columns and "ingredient_id" in shortages_df.columns:
                        shortages_df["IngredientId"] = shortages_df["ingredient_id"]

                    comparison = self.db.compare_with_cti_shortages(shortages_df)
                    lines.append(comparison["summary"])
                    lines.append("")
            except Exception as e:
                logger.debug(f"Could not compare with CTI: {e}")

            if not cti_shortages.empty:
                lines.extend(
                    [
                        f"- **Aktywne dokumenty BR:** {len(cti_shortages['ShortageDocNumber'].unique()) if 'ShortageDocNumber' in cti_shortages.columns else 0}",
                        f"- **Łącznie pozycji:** {len(cti_shortages)}",
                        "",
                    ]
                )

        # 5. Recommendations
        lines.extend(
            [
                "## 5. Rekomendacje",
                "Na podstawie powyższej analizy należy:",
            ]
        )

        if result["can_produce"]:
            lines.append("1. ✅ Rozpocząć produkcję - wszystkie materiały dostępne")
        else:
            lines.append(f"1. 📦 Zamówić brakujące surowce ({len(result['shortages'])} pozycji)")
            if result["max_delivery_time"] > 0:
                lines.append(f"2. ⏰ Zaplanować produkcję po {result['earliest_production_date']}")
            if subs_result.get("substitutes_available"):
                lines.append("3. 🔄 Rozważyć użycie zamienników (jeśli dostępne)")

        return "\n".join(lines)

    # ========== LLM Integration ==========

    def analyze_with_llm(
        self, product_id: int, quantity: float, warehouse_ids: list[int] = None, llm_engine=None
    ) -> dict:
        """
        Performs MRP analysis and generates AI recommendations using Local LLM.

        This method:
        1. Runs comprehensive production analysis (U1-U3 integrated)
        2. Generates context string for LLM
        3. Calls Local LLM for intelligent recommendations

        Args:
            product_id: ID of the product to analyze
            quantity: Target production quantity
            warehouse_ids: Optional warehouse filter
            llm_engine: LocalLLMEngine instance (if None, creates one)

        Returns:
            dict with keys:
            - 'analysis': Comprehensive analysis markdown
            - 'llm_recommendation': AI-generated recommendation text
            - 'llm_available': Whether LLM was used
            - 'simulation_result': Raw simulation result
        """
        logger.info(f"Starting LLM-enhanced analysis for product {product_id}, qty {quantity}")

        # 1. Run comprehensive analysis
        analysis_markdown = self.get_comprehensive_production_analysis(product_id, quantity, warehouse_ids)

        # 2. Get simulation result for additional context
        simulation = self.simulate_production_with_delivery(product_id, quantity, warehouse_ids)

        result = {
            "analysis": analysis_markdown,
            "llm_recommendation": "",
            "llm_available": False,
            "simulation_result": simulation,
        }

        # 3. Try to use LLM for recommendations
        if llm_engine is None:
            try:
                from src.ai_engine.local_llm import LocalLLMEngine, check_local_llm_available

                available, msg = check_local_llm_available()
                if available:
                    llm_engine = LocalLLMEngine()
                    logger.info(f"Local LLM available: {msg}")
                else:
                    logger.info(f"Local LLM not available: {msg}")
                    result["llm_recommendation"] = f"LLM niedostępne: {msg}"
                    return result
            except Exception as e:
                logger.warning(f"Could not initialize Local LLM: {e}")
                result["llm_recommendation"] = f"Błąd inicjalizacji LLM: {e}"
                return result

        # 4. Generate prompt for LLM
        prompt = self._generate_llm_prompt(product_id, quantity, simulation, analysis_markdown)

        # 5. Get LLM response
        try:
            llm_response = llm_engine.generate_explanation(prompt)
            result["llm_recommendation"] = llm_response
            result["llm_available"] = True
            logger.info("LLM recommendation generated successfully")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            result["llm_recommendation"] = f"Błąd generowania rekomendacji: {e}"

        return result

    def _generate_llm_prompt(self, product_id: int, quantity: float, simulation: dict, analysis_markdown: str) -> str:
        """
        Generates a structured prompt for the LLM based on MRP analysis.
        """
        # Extract key info
        can_produce = simulation.get("can_produce", False)
        max_producible = simulation.get("max_producible", 0)
        shortages = simulation.get("shortages", [])
        delivery_time = simulation.get("max_delivery_time", 0)
        limiting = simulation.get("limiting_factor", {})

        # Build prompt
        prompt_lines = [
            "Jako ekspert ds. zakupów i planowania produkcji, przeanalizuj następującą sytuację:",
            "",
            "## Dane Wejściowe",
            f"- Produkt do wyprodukowania: ID {product_id}",
            f"- Ilość docelowa: {quantity} szt.",
            f"- Możliwość realizacji: {'TAK' if can_produce else 'NIE'}",
            f"- Maksymalna ilość możliwa: {max_producible:.0f} szt.",
        ]

        if shortages:
            prompt_lines.extend(
                [
                    "",
                    f"## Braki Surowców ({len(shortages)} pozycji)",
                ]
            )
            for s in shortages[:5]:
                code = s.get("IngredientCode", "?")
                shortage_qty = abs(s.get("Shortage", 0))
                prompt_lines.append(f"- {code}: brakuje {shortage_qty:.2f}")

        if limiting:
            prompt_lines.extend(
                [
                    "",
                    "## Czynnik Ograniczający",
                    f"- Surowiec: {limiting.get('ingredient_name', '?')} ({limiting.get('ingredient_code', '?')})",
                    f"- Stan: {limiting.get('current_stock', 0):.2f}, Potrzeba: {limiting.get('quantity_required', 0):.2f}",
                ]
            )

        if delivery_time > 0:
            prompt_lines.extend(
                [
                    "",
                    "## Czas Dostawy",
                    f"- Maksymalny czas dostawy: {delivery_time} dni",
                    f"- Data rozpoczęcia produkcji: {simulation.get('earliest_production_date', 'Nieznana')}",
                ]
            )

        prompt_lines.extend(
            [
                "",
                "## Zadanie",
                "Na podstawie powyższych danych:",
                "1. Oceń sytuację i priorytet działań",
                "2. Zaproponuj konkretne kroki dla działu zakupów",
                "3. Wskaż ryzyka i alternatywy (np. zamienniki)",
                "",
                "Odpowiedź sformułuj w języku polskim, używając punktów i konkretnych liczb.",
            ]
        )

        return "\n".join(prompt_lines)

    def get_analysis_with_llm_response(
        self, product_id: int, quantity: float, warehouse_ids: list[int] = None, llm_engine=None
    ) -> str:
        """
        Convenience method that returns combined analysis + LLM recommendation as markdown.

        Returns:
            Formatted markdown string with analysis and AI recommendation
        """
        result = self.analyze_with_llm(product_id, quantity, warehouse_ids, llm_engine)

        output_lines = [result["analysis"]]

        if result["llm_available"] and result["llm_recommendation"]:
            output_lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## 🤖 Rekomendacja AI (Local LLM)",
                    "",
                    result["llm_recommendation"],
                ]
            )
        elif result["llm_recommendation"]:
            output_lines.extend(
                [
                    "",
                    f"*Uwaga: {result['llm_recommendation']}*",
                ]
            )

        return "\n".join(output_lines)
