"""
MRP (Material Requirements Planning) Logic Tests.
Tests shortage calculations, BOM processing, and simulation accuracy.

Verifies business logic correctness without database requirements.
"""

import numpy as np
import pandas as pd
import pytest


class TestShortageCalculation:
    """Test shortage formula: Shortage = CurrentStock - QuantityRequired"""

    def test_shortage_when_stock_insufficient(self):
        """When stock < required, shortage should be negative."""
        from src.services.mrp_simulator import MRPSimulator

        # Create mock DB that returns controlled BOM data
        class MockDB:
            def get_bom_with_stock(self, product_id, technology_id=None, warehouse_ids=None):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001", "MAT002"],
                        "IngredientName": ["Material A", "Material B"],
                        "QuantityPerUnit": [10.0, 5.0],  # Per unit of final product
                        "Unit": ["kg", "kg"],
                        "CurrentStock": [75.0, 100.0],  # Available stock
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        # MAT001: Required = 10 * 10 = 100, Stock = 75, Shortage = 75 - 100 = -25
        # MAT002: Required = 10 * 5 = 50, Stock = 100, Shortage = 100 - 50 = +50 (OK)
        bom = result["bom"]

        mat001 = bom[bom["IngredientCode"] == "MAT001"].iloc[0]
        assert mat001["QuantityRequired"] == 100.0  # 10 * 10
        assert mat001["Shortage"] == -25.0  # 75 - 100
        assert mat001["Status"] == "KRYTYCZNY"

        mat002 = bom[bom["IngredientCode"] == "MAT002"].iloc[0]
        assert mat002["QuantityRequired"] == 50.0  # 10 * 5
        assert mat002["Shortage"] == 50.0  # 100 - 50
        assert mat002["Status"] == "OK"

    def test_shortage_when_stock_sufficient(self):
        """When stock >= required, no shortage."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, product_id, technology_id=None, warehouse_ids=None):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001"],
                        "IngredientName": ["Material A"],
                        "QuantityPerUnit": [5.0],
                        "Unit": ["kg"],
                        "CurrentStock": [100.0],
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        # Required = 10 * 5 = 50, Stock = 100
        assert result["can_produce"] is True
        assert result["shortages"] == []

    def test_can_produce_false_when_any_shortage(self):
        """can_produce should be False if ANY ingredient has shortage."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, product_id, technology_id=None, warehouse_ids=None):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001", "MAT002", "MAT003"],
                        "IngredientName": ["A", "B", "C"],
                        "QuantityPerUnit": [1.0, 1.0, 1.0],
                        "Unit": ["kg", "kg", "kg"],
                        "CurrentStock": [100.0, 100.0, 5.0],  # MAT003 will cause shortage
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        # MAT003: Required = 10, Stock = 5 → Shortage
        assert result["can_produce"] is False
        assert len(result["shortages"]) == 1
        assert result["shortages"][0]["IngredientCode"] == "MAT003"

    def test_max_producible_calculation(self):
        """max_producible = min(stock / quantity_per_unit) across all ingredients."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, product_id, technology_id=None, warehouse_ids=None):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001", "MAT002"],
                        "IngredientName": ["A", "B"],
                        "QuantityPerUnit": [10.0, 5.0],
                        "Unit": ["kg", "kg"],
                        "CurrentStock": [50.0, 100.0],  # 50/10=5, 100/5=20 → min=5
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        # MAT001 limits to 50/10 = 5 units
        # MAT002 allows 100/5 = 20 units
        # Max producible = min(5, 20) = 5
        assert result["max_producible"] == 5.0

    def test_limiting_factor_identification(self):
        """Limiting factor should be the ingredient with lowest max_producible."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, product_id, technology_id=None, warehouse_ids=None):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["ABUNDANT", "SCARCE"],
                        "IngredientName": ["Abundant Material", "Scarce Material"],
                        "QuantityPerUnit": [1.0, 10.0],
                        "Unit": ["kg", "kg"],
                        "CurrentStock": [1000.0, 50.0],  # 1000/1=1000, 50/10=5
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        assert result["limiting_factor"]["ingredient_code"] == "SCARCE"
        assert result["limiting_factor"]["max_producible"] == 5.0


class TestCalculateShortagesMethod:
    """Test the calculate_shortages utility method."""

    def test_filters_only_negative_shortage(self):
        """Should return only items where Shortage < 0."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            pass

        simulator = MRPSimulator(MockDB())

        bom_df = pd.DataFrame(
            {
                "IngredientCode": ["OK1", "OK2", "SHORT1", "SHORT2"],
                "IngredientName": ["Ok 1", "Ok 2", "Short 1", "Short 2"],
                "QuantityPerUnit": [1.0, 1.0, 1.0, 1.0],
                "CurrentStock": [100.0, 50.0, 5.0, 0.0],
                "Unit": ["kg", "kg", "kg", "kg"],
            }
        )

        result = simulator.calculate_shortages(bom_df, target_quantity=10)

        # OK1: 100-10=90 (OK), OK2: 50-10=40 (OK)
        # SHORT1: 5-10=-5 (SHORT), SHORT2: 0-10=-10 (SHORT)
        assert len(result) == 2
        assert "SHORT1" in result["IngredientCode"].values
        assert "SHORT2" in result["IngredientCode"].values

    def test_to_order_is_positive_shortage(self):
        """ToOrder should be abs(Shortage) - the amount to purchase."""
        from src.services.mrp_simulator import MRPSimulator

        simulator = MRPSimulator(None)

        bom_df = pd.DataFrame(
            {
                "IngredientCode": ["MAT001"],
                "IngredientName": ["Material"],
                "QuantityPerUnit": [10.0],
                "CurrentStock": [25.0],
                "Unit": ["kg"],
            }
        )

        result = simulator.calculate_shortages(bom_df, target_quantity=10)

        # Required = 100, Stock = 25, Shortage = -75, ToOrder = 75
        assert len(result) == 1
        assert result.iloc[0]["ToOrder"] == 75.0


class TestStatusClassification:
    """Test status classification logic (OK, BRAK, KRYTYCZNY)."""

    def test_status_ok_when_no_shortage(self):
        """Status OK when Shortage >= 0."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, *args, **kwargs):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001"],
                        "IngredientName": ["Material"],
                        "QuantityPerUnit": [1.0],
                        "CurrentStock": [100.0],
                        "Unit": ["kg"],
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=50)

        # Stock=100, Required=50, Shortage=50 (positive)
        assert result["bom"].iloc[0]["Status"] == "OK"

    def test_status_brak_when_small_shortage(self):
        """Status BRAK when shortage is within 10% of required."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, *args, **kwargs):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001"],
                        "IngredientName": ["Material"],
                        "QuantityPerUnit": [10.0],
                        "CurrentStock": [95.0],
                        "Unit": ["kg"],
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        # Required=100, Stock=95, Shortage=-5
        # -5 >= -100*0.1 = -10, so BRAK (not KRYTYCZNY)
        assert result["bom"].iloc[0]["Status"] == "BRAK"

    def test_status_krytyczny_when_large_shortage(self):
        """Status KRYTYCZNY when shortage exceeds 10% of required."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, *args, **kwargs):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001"],
                        "IngredientName": ["Material"],
                        "QuantityPerUnit": [10.0],
                        "CurrentStock": [50.0],
                        "Unit": ["kg"],
                    }
                )

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        # Required=100, Stock=50, Shortage=-50
        # -50 < -100*0.1 = -10, so KRYTYCZNY
        assert result["bom"].iloc[0]["Status"] == "KRYTYCZNY"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_bom_returns_error(self):
        """When no BOM exists, should return error."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, *args, **kwargs):
                return pd.DataFrame()

        simulator = MRPSimulator(MockDB())
        result = simulator.simulate_production(product_id=1, quantity=10)

        assert result["can_produce"] is False
        assert "error" in result

    def test_zero_quantity_per_unit_handled(self):
        """Should handle zero quantity per unit without division error."""
        from src.services.mrp_simulator import MRPSimulator

        class MockDB:
            def get_bom_with_stock(self, *args, **kwargs):
                return pd.DataFrame(
                    {
                        "IngredientCode": ["MAT001"],
                        "IngredientName": ["Material"],
                        "QuantityPerUnit": [0.0],  # Edge case
                        "CurrentStock": [100.0],
                        "Unit": ["kg"],
                    }
                )

        simulator = MRPSimulator(MockDB())

        # Should not raise ZeroDivisionError
        # max_producible = 100 / 0 → inf (acceptable) or handled
        try:
            result = simulator.simulate_production(product_id=1, quantity=10)
            # If it returns, max_producible should be infinity or very large
            assert result["max_producible"] >= 0 or np.isinf(result["max_producible"])
        except ZeroDivisionError:
            pytest.fail("Zero quantity per unit caused ZeroDivisionError")
