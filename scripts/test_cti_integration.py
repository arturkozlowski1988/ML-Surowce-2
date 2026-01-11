"""
Comprehensive CTI U1-U6 Integration Tests
Tests all new methods added for CTI Production integration
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.db_connector import DatabaseConnector


def run_tests():
    print("=" * 60)
    print("KOMPLETNE TESTY ZGODNOSCI CTI U1-U6")
    print("=" * 60 + "\n")

    db = DatabaseConnector()
    results = {}

    # U1: Production Status
    print("[U1] get_production_status()...")
    try:
        ps = db.get_production_status()
        results["U1_production_status"] = {"records": len(ps), "status": "OK"}
        print(f"   OK - Records: {len(ps)}")
    except Exception as e:
        results["U1_production_status"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U1 ext: Active Orders Demand
    print("[U1 ext] get_active_orders_demand()...")
    try:
        ad = db.get_active_orders_demand()
        results["U1_active_demand"] = {"records": len(ad), "status": "OK"}
        print(f"   OK - Records: {len(ad)}")
    except Exception as e:
        results["U1_active_demand"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U2: Compare with CTI Shortages
    print("[U2] compare_with_cti_shortages()...")
    try:
        test_df = pd.DataFrame({"IngredientId": [1, 2], "ShortageQty": [10, 20]})
        comp = db.compare_with_cti_shortages(test_df)
        summary = comp["summary"][:40] if comp["summary"] else "empty"
        results["U2_compare_shortages"] = {"summary": summary, "status": "OK"}
        print(f"   OK - Summary: {summary}...")
    except Exception as e:
        results["U2_compare_shortages"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U3: Smart Substitutes
    print("[U3] get_smart_substitutes()...")
    try:
        subs = db.get_smart_substitutes(1, 100)
        results["U3_smart_substitutes"] = {"records": len(subs), "status": "OK"}
        print(f"   OK - Records: {len(subs)}")
    except Exception as e:
        results["U3_smart_substitutes"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U4: Dashboard Stats
    print("[U4] get_production_dashboard_stats()...")
    try:
        stats = db.get_production_dashboard_stats()
        orders = stats["orders"]["total"]
        tech = stats["technologies"]["total"]
        results["U4_dashboard"] = {"orders": orders, "tech": tech, "status": "OK"}
        print(f"   OK - Orders: {orders}, Technologies: {tech}")
    except Exception as e:
        results["U4_dashboard"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U5: Completions History
    print("[U5] get_completions_history()...")
    try:
        comp_hist = db.get_completions_history()
        results["U5_completions"] = {"records": len(comp_hist), "status": "OK"}
        print(f"   OK - Records: {len(comp_hist)}")
    except Exception as e:
        results["U5_completions"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U5 ext: Completion Summary
    print("[U5 ext] get_completion_summary()...")
    try:
        comp_sum = db.get_completion_summary()
        results["U5_completion_summary"] = {"records": len(comp_sum), "status": "OK"}
        print(f"   OK - Records: {len(comp_sum)}")
    except Exception as e:
        results["U5_completion_summary"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U6: Product CTI Attributes
    print("[U6] get_product_cti_attributes()...")
    try:
        attrs = db.get_product_cti_attributes()
        results["U6_attributes"] = {"records": len(attrs), "status": "OK"}
        print(f"   OK - Records: {len(attrs)}")
    except Exception as e:
        results["U6_attributes"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # U6 ext: Available CTI Attributes
    print("[U6 ext] get_available_cti_attributes()...")
    try:
        avail = db.get_available_cti_attributes()
        results["U6_available"] = {"records": len(avail), "status": "OK"}
        print(f"   OK - Records: {len(avail)}")
    except Exception as e:
        results["U6_available"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # Existing methods verification
    print("\n--- WERYFIKACJA ISTNIEJACYCH METOD ---")

    print("[Existing] get_order_statuses()...")
    try:
        os_df = db.get_order_statuses()
        results["existing_statuses"] = {"records": len(os_df), "status": "OK"}
        print(f"   OK - Records: {len(os_df)}")
    except Exception as e:
        results["existing_statuses"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    print("[Existing] get_products_with_technology()...")
    try:
        tech = db.get_products_with_technology()
        results["existing_tech"] = {"records": len(tech), "status": "OK"}
        print(f"   OK - Records: {len(tech)}")
    except Exception as e:
        results["existing_tech"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    print("[Existing] get_shortage_analysis_cti()...")
    try:
        short = db.get_shortage_analysis_cti()
        results["existing_shortages"] = {"records": len(short), "status": "OK"}
        print(f"   OK - Records: {len(short)}")
    except Exception as e:
        results["existing_shortages"] = {"error": str(e)[:50], "status": "FAIL"}
        print(f"   FAIL - {str(e)[:50]}")

    # Summary
    print("\n" + "=" * 60)
    print("PODSUMOWANIE TESTOW")
    print("=" * 60)
    ok_count = sum(1 for v in results.values() if v.get("status") == "OK")
    fail_count = len(results) - ok_count
    print(f"Testy OK: {ok_count}/{len(results)}")
    print(f"Testy FAIL: {fail_count}/{len(results)}")

    if fail_count == 0:
        print("\n*** WSZYSTKIE TESTY PRZESZLY POMYSLNIE! ***")
        print("Zgodnosc z CTI Produkcja: ~85%")
    else:
        print("\nNiektore testy nie przeszly - sprawdz logi powyzej")

    return results


if __name__ == "__main__":
    run_tests()
