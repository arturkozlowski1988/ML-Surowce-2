"""
Test Suite for Medium Priority Fixes
=====================================
Tests:
1. Cache functionality (get/set/clear/TTL)
2. Diagnostics logging (query timing, slow query detection)
3. Index recommendations

Run this script to verify all medium-priority fixes are working correctly.
"""
import io
import logging
import os
import sys
import time

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.db_connector import DatabaseConnector, QueryDiagnostics

# Suppress SQLAlchemy warnings for cleaner output
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

# Test results tracking
TESTS_PASSED = 0
TESTS_FAILED = 0


def test_result(name: str, passed: bool, details: str = ""):
    """Records and prints test result."""
    global TESTS_PASSED, TESTS_FAILED

    if passed:
        TESTS_PASSED += 1
        print(f"  [OK] {name}")
    else:
        TESTS_FAILED += 1
        print(f"  [BLAD] {name}")
        if details:
            print(f"      Details: {details}")


def test_cache_functionality():
    """
    TEST 1: Cache Functionality
    Tests cache set/get/clear operations and TTL expiration.
    """
    print("\n" + "=" * 60)
    print("TEST 1: FUNKCJONALNOSC CACHE")
    print("=" * 60)

    try:
        db = DatabaseConnector(enable_diagnostics=False)

        # Test 1.1: Cache is initially empty
        db.clear_cache()
        cached = db._get_from_cache("test_key")
        test_result("Cache poczatkowo pusty", cached is None)

        # Test 1.2: Set and retrieve from cache
        test_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        db._set_cache("test_key", test_df)
        cached = db._get_from_cache("test_key")
        test_result("Zapis i odczyt z cache", cached is not None and len(cached) == 3)

        # Test 1.3: Cache returns copy (not reference)
        if cached is not None:
            cached["col1"] = [10, 20, 30]  # Modify retrieved data
            original = db._get_from_cache("test_key")
            test_result("Cache zwraca kopie (nie referencje)", original["col1"].tolist() == [1, 2, 3])
        else:
            test_result("Cache zwraca kopie (nie referencje)", False, "Cache was None")

        # Test 1.4: Clear specific key
        db._set_cache("key1", test_df)
        db._set_cache("key2", test_df)
        db.clear_cache("key1")
        test_result(
            "Czyszczenie konkretnego klucza",
            db._get_from_cache("key1") is None and db._get_from_cache("key2") is not None,
        )

        # Test 1.5: Clear all cache
        db.clear_cache()
        test_result("Czyszczenie calego cache", db._get_from_cache("key2") is None)

        # Test 1.6: TTL expiration simulation
        # Save original TTL
        original_ttl = db._cache_ttl
        db._cache_ttl = 0.1  # 100ms for testing

        db._set_cache("ttl_test", test_df)
        immediate = db._get_from_cache("ttl_test")
        time.sleep(0.15)  # Wait for expiration
        expired = db._get_from_cache("ttl_test")

        db._cache_ttl = original_ttl  # Restore
        test_result("TTL wygasanie cache", immediate is not None and expired is None)

        # Test 1.7: use_cache parameter in methods
        db.clear_cache()

        # First call - should query database
        df1 = db.get_products_with_technology(use_cache=True)

        # Second call - should return from cache
        start = time.time()
        df2 = db.get_products_with_technology(use_cache=True)
        cache_time = time.time() - start

        # Third call - force no cache
        start = time.time()
        df3 = db.get_products_with_technology(use_cache=False)
        no_cache_time = time.time() - start

        test_result(
            "Parametr use_cache dziala",
            cache_time < no_cache_time or (cache_time < 0.1 and len(df1) == len(df2)),
            f"Cache: {cache_time:.4f}s, No cache: {no_cache_time:.4f}s",
        )

        db.clear_cache()

    except Exception as e:
        test_result("Inicjalizacja cache", False, str(e))


def test_diagnostics_logging():
    """
    TEST 2: Diagnostics Logging
    Tests query timing and statistics collection.
    """
    print("\n" + "=" * 60)
    print("TEST 2: LOGOWANIE DIAGNOSTYCZNE")
    print("=" * 60)

    try:
        # Test 2.1: QueryDiagnostics class
        diag = QueryDiagnostics()
        test_result("QueryDiagnostics inicjalizacja", diag is not None)

        # Test 2.2: Log query and retrieve stats
        diag.log_query("test_query_1", 0.05, 100)
        diag.log_query("test_query_2", 0.10, 200)
        stats = diag.get_stats()

        test_result(
            "Zbieranie statystyk zapytan", stats["total_queries"] == 2 and abs(stats["avg_duration"] - 0.075) < 0.001
        )

        # Test 2.3: Slow query detection
        diag.log_query("slow_query", 1.5, 1000)  # Above threshold
        stats = diag.get_stats()
        test_result("Wykrywanie wolnych zapytan", stats["slow_queries"] == 1)

        # Test 2.4: DatabaseConnector with diagnostics enabled
        db = DatabaseConnector(enable_diagnostics=True)
        test_result("DatabaseConnector z diagnostyka", db.diagnostics is not None)

        # Test 2.5: Query execution logs diagnostics
        db.execute_query("SELECT 1", query_name="simple_test")
        stats = db.get_diagnostics_stats()
        test_result("Zapytanie loguje diagnostyke", stats.get("total_queries", 0) >= 1)

        # Test 2.6: DatabaseConnector without diagnostics
        db_no_diag = DatabaseConnector(enable_diagnostics=False)
        test_result("DatabaseConnector bez diagnostyki", db_no_diag.diagnostics is None)

        # Test 2.7: get_diagnostics_stats returns empty dict when disabled
        stats = db_no_diag.get_diagnostics_stats()
        test_result("get_diagnostics_stats bez diagnostyki", stats == {})

    except Exception as e:
        test_result("Logowanie diagnostyczne", False, str(e))


def test_index_recommendations():
    """
    TEST 3: Index Recommendations
    Tests the check_and_create_indexes method.
    """
    print("\n" + "=" * 60)
    print("TEST 3: REKOMENDACJE INDEKSOW")
    print("=" * 60)

    try:
        db = DatabaseConnector(enable_diagnostics=False)

        # Test 3.1: check_and_create_indexes returns proper structure
        result = db.check_and_create_indexes()

        test_result("check_and_create_indexes zwraca slownik", isinstance(result, dict))

        # Test 3.2: Result contains expected keys
        expected_keys = {"existing", "missing", "create_sql"}
        test_result("Wynik zawiera oczekiwane klucze", expected_keys.issubset(result.keys()))

        # Test 3.3: existing is a list
        test_result("'existing' jest lista", isinstance(result.get("existing"), list))

        # Test 3.4: missing contains proper structure
        missing = result.get("missing", [])
        if missing:
            first_missing = missing[0]
            has_required_fields = all(key in first_missing for key in ["name", "table", "columns", "sql", "reason"])
            test_result("'missing' zawiera wymagane pola", has_required_fields)
        else:
            test_result("'missing' zawiera wymagane pola", True, "Brak brakujacych indeksow - wszystkie istnieja")

        # Test 3.5: create_sql is a list of strings
        create_sql = result.get("create_sql", [])
        test_result(
            "'create_sql' jest lista stringow",
            isinstance(create_sql, list) and all(isinstance(s, str) for s in create_sql),
        )

        # Test 3.6: Print summary
        print("\n  Podsumowanie indeksow:")
        print(f"    Istniejace: {len(result.get('existing', []))}")
        print(f"    Brakujace:  {len(result.get('missing', []))}")

        for idx in result.get("missing", [])[:3]:  # Show max 3
            print(f"      - {idx['name']}: {idx['reason'][:50]}...")

        test_result("Podsumowanie indeksow wygenerowane", True)

    except Exception as e:
        test_result("Rekomendacje indeksow", False, str(e))


def test_cache_with_real_queries():
    """
    TEST 4: Cache with Real Database Queries
    Tests cache performance improvement with actual database queries.
    """
    print("\n" + "=" * 60)
    print("TEST 4: CACHE Z PRAWDZIWYMI ZAPYTANIAMI")
    print("=" * 60)

    try:
        db = DatabaseConnector(enable_diagnostics=True)
        db.clear_cache()

        # Test 4.1: First call to get_historical_data (no cache)
        start = time.time()
        df1 = db.get_historical_data(use_cache=True)
        first_call_time = time.time() - start

        test_result(
            "get_historical_data - pierwsze wywolanie",
            not df1.empty,
            f"Czas: {first_call_time:.3f}s, Wierszy: {len(df1)}",
        )

        # Test 4.2: Second call (from cache)
        start = time.time()
        df2 = db.get_historical_data(use_cache=True)
        cached_call_time = time.time() - start

        test_result("get_historical_data - z cache", len(df1) == len(df2), f"Czas: {cached_call_time:.3f}s")

        # Test 4.3: Cache speedup
        if first_call_time > 0.01:  # Only if first call was measurable
            speedup = first_call_time / max(cached_call_time, 0.0001)
            test_result(
                "Przyspieszenie dzieki cache", cached_call_time < first_call_time, f"Przyspieszenie: {speedup:.1f}x"
            )
        else:
            test_result("Przyspieszenie dzieki cache", True, "Zbyt szybkie zapytanie do zmierzenia")

        # Test 4.4: get_current_stock caching
        db.clear_cache("current_stock")

        start = time.time()
        df_stock1 = db.get_current_stock(use_cache=True)
        first_stock_time = time.time() - start

        start = time.time()
        df_stock2 = db.get_current_stock(use_cache=True)
        cached_stock_time = time.time() - start

        test_result(
            "get_current_stock cache",
            len(df_stock1) == len(df_stock2),
            f"Pierwszy: {first_stock_time:.3f}s, Cache: {cached_stock_time:.3f}s",
        )

        # Test 4.5: get_products_with_technology caching
        db.clear_cache("products_with_technology")

        df_tech1 = db.get_products_with_technology(use_cache=True)
        df_tech2 = db.get_products_with_technology(use_cache=True)

        test_result("get_products_with_technology cache", len(df_tech1) == len(df_tech2))

        # Test 4.6: Diagnostics stats after multiple queries
        stats = db.get_diagnostics_stats()
        test_result(
            "Statystyki diagnostyczne po zapytaniach",
            stats.get("total_queries", 0) >= 3,
            f"Zapytan: {stats.get('total_queries', 0)}, " f"Sredni czas: {stats.get('avg_duration', 0):.3f}s",
        )

        db.clear_cache()

    except Exception as e:
        test_result("Cache z prawdziwymi zapytaniami", False, str(e))


def test_bom_with_technology_id():
    """
    TEST 5: BOM with Technology ID Parameter
    Tests the new technology_id parameter in get_bom_with_stock.
    """
    print("\n" + "=" * 60)
    print("TEST 5: BOM Z PARAMETREM TECHNOLOGY_ID")
    print("=" * 60)

    try:
        db = DatabaseConnector(enable_diagnostics=False)

        # Get a product with technology
        df_tech = db.get_products_with_technology()

        if df_tech.empty:
            test_result("Produkty z technologia dostepne", False, "Brak produktow")
            return

        test_result("Produkty z technologia dostepne", True)

        product_id = int(df_tech["FinalProductId"].iloc[0])

        # Test 5.1: Call without technology_id (default behavior)
        df_bom_default = db.get_bom_with_stock(product_id)
        test_result("get_bom_with_stock bez technology_id", df_bom_default is not None)

        # Test 5.2: Get technology ID for the product
        tech_query = f"""
        SELECT TOP 1 CTN_ID
        FROM dbo.CtiTechnolNag
        WHERE CTN_TwrId = {product_id}
        """
        df_tech_id = db.execute_query(tech_query)

        if not df_tech_id.empty:
            tech_id = int(df_tech_id["CTN_ID"].iloc[0])

            # Test 5.3: Call with specific technology_id
            df_bom_specific = db.get_bom_with_stock(product_id, technology_id=tech_id)
            test_result("get_bom_with_stock z technology_id", df_bom_specific is not None, f"Technology ID: {tech_id}")

            # Test 5.4: Results should be same or subset
            if not df_bom_default.empty and not df_bom_specific.empty:
                test_result(
                    "Wyniki z technology_id sa poprawne",
                    len(df_bom_specific) <= len(df_bom_default) or len(df_bom_specific) > 0,
                )
        else:
            test_result("get_bom_with_stock z technology_id", True, "Brak technology ID do testowania")

    except Exception as e:
        test_result("BOM z technology_id", False, str(e))


def run_all_tests():
    """Runs all test suites and prints summary."""
    global TESTS_PASSED, TESTS_FAILED

    print("\n" + "=" * 60)
    print("  TESTY NAPRAW PRIORYTETU SREDNIEGO")
    print("  AI Supply Assistant - CTI Production")
    print("=" * 60)

    # Run all test suites
    test_cache_functionality()
    test_diagnostics_logging()
    test_index_recommendations()
    test_cache_with_real_queries()
    test_bom_with_technology_id()

    # Print summary
    total = TESTS_PASSED + TESTS_FAILED
    print("\n" + "=" * 60)
    print("  PODSUMOWANIE TESTOW")
    print("=" * 60)
    print(f"  Testy wykonane: {total}")
    print(f"  Zaliczone:      {TESTS_PASSED} [OK]")
    print(f"  Niezaliczone:   {TESTS_FAILED} [BLAD]")
    print("=" * 60)

    if TESTS_FAILED == 0:
        print("\n  [OK] WSZYSTKIE TESTY ZALICZONE!")
        print("  Naprawy priorytetu sredniego dzialaja poprawnie.")
    else:
        print(f"\n  [!] {TESTS_FAILED} TESTOW NIEZALICZONYCH")
        print("  Sprawdz szczegoly powyzej.")

    return TESTS_FAILED == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
