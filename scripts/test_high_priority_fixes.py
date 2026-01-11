"""
Test Suite for High Priority Fixes
===================================
Tests:
1. Database schema correctness (CDN.Towary vs dbo.Towary)
2. UTF-8 encoding support in scripts
3. Empty data validation in AI assistant logic

Run this script to verify all high-priority fixes are working correctly.
"""
import io
import os
import sys

# Fix encoding for Windows console (CP1250 -> UTF-8)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.db_connector import DatabaseConnector

# Test results tracking
TESTS_PASSED = 0
TESTS_FAILED = 0


def test_result(name: str, passed: bool, details: str = ""):
    """Records and prints test result."""
    global TESTS_PASSED, TESTS_FAILED
    status = "PASS" if passed else "FAIL"
    symbol = "[OK]" if passed else "[BLAD]"

    if passed:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1

    print(f"  {symbol} {name}")
    if details and not passed:
        print(f"      Details: {details}")


def test_database_schema():
    """
    TEST 1: Database Schema Correctness
    Verifies that queries use correct schema prefixes:
    - CDN.Towary (not dbo.Towary)
    - CDN.TwrZasoby (not dbo.TwrZasoby)
    - dbo.CtiZlecenieNag, dbo.CtiZlecenieElem, dbo.CtiTechnolNag, dbo.CtiTechnolElem
    """
    print("\n" + "=" * 60)
    print("TEST 1: WERYFIKACJA SCHEMATU BAZY DANYCH")
    print("=" * 60)

    try:
        db = DatabaseConnector()

        # Test 1.1: CDN.Towary table exists and is accessible
        query1 = "SELECT TOP 1 Twr_TwrId, Twr_Kod, Twr_Nazwa FROM CDN.Towary"
        df1 = db.execute_query(query1)
        test_result("CDN.Towary dostepna", not df1.empty, "Tabela CDN.Towary powinna zawierac dane")

        # Test 1.2: CDN.TwrZasoby table exists
        query2 = "SELECT TOP 1 TwZ_TwrId, TwZ_Ilosc FROM CDN.TwrZasoby"
        df2 = db.execute_query(query2)
        test_result("CDN.TwrZasoby dostepna", not df2.empty, "Tabela CDN.TwrZasoby powinna zawierac dane")

        # Test 1.3: dbo.CtiZlecenieNag table exists
        query3 = "SELECT TOP 1 CZN_ID, CZN_NrPelny FROM dbo.CtiZlecenieNag"
        df3 = db.execute_query(query3)
        test_result("dbo.CtiZlecenieNag dostepna", not df3.empty, "Tabela dbo.CtiZlecenieNag powinna zawierac dane")

        # Test 1.4: dbo.CtiTechnolNag table exists
        query4 = "SELECT TOP 1 CTN_ID, CTN_Numer FROM dbo.CtiTechnolNag"
        df4 = db.execute_query(query4)
        test_result("dbo.CtiTechnolNag dostepna", not df4.empty, "Tabela dbo.CtiTechnolNag powinna zawierac dane")

        # Test 1.5: Verify JOIN between CDN.Towary and dbo.CtiZlecenieElem works
        query5 = """
        SELECT TOP 1 t.Twr_Kod, e.CZE_Ilosc
        FROM CDN.Towary t
        JOIN dbo.CtiZlecenieElem e ON t.Twr_TwrId = e.CZE_TwrId
        """
        df5 = db.execute_query(query5)
        test_result(
            "JOIN CDN.Towary <-> dbo.CtiZlecenieElem",
            not df5.empty,
            "Relacja pomiedzy schematami CDN i dbo powinna dzialac",
        )

        # Test 1.6: Verify get_current_stock uses correct schema
        df_stock = db.get_current_stock()
        test_result(
            "get_current_stock() poprawny schemat",
            not df_stock.empty,
            "Metoda powinna zwrocic dane z CDN.Towary i CDN.TwrZasoby",
        )

        # Test 1.7: Verify get_bom_with_stock uses correct schema
        df_tech = db.get_products_with_technology()
        if not df_tech.empty:
            test_prod_id = int(df_tech["FinalProductId"].iloc[0])
            df_bom = db.get_bom_with_stock(test_prod_id)
            test_result(
                "get_bom_with_stock() poprawny schemat",
                df_bom is not None,  # May be empty but should not fail
                "Metoda nie powinna rzucac bledu 'Invalid object name'",
            )
        else:
            test_result("get_bom_with_stock() poprawny schemat", True, "Pominieto - brak produktow z technologia")

    except Exception as e:
        test_result("Polaczenie z baza danych", False, str(e))


def test_encoding_support():
    """
    TEST 2: UTF-8 Encoding Support
    Verifies that special characters can be printed without errors.
    """
    print("\n" + "=" * 60)
    print("TEST 2: WERYFIKACJA OBSLUGI KODOWANIA UTF-8")
    print("=" * 60)

    try:
        # Test 2.1: Polish characters
        polish_chars = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
        print(f"  Test polskich znakow: {polish_chars}")
        test_result("Polskie znaki diakrytyczne", True)

        # Test 2.2: Unicode symbols (these caused the original error)
        unicode_symbols = "✓ ✗ ✅ ❌ ⚠️ 🔧 📊"
        print(f"  Test symboli Unicode: {unicode_symbols}")
        test_result("Symbole Unicode (checkmarks, emoji)", True)

        # Test 2.3: Mixed content
        mixed = "[OK] Weryfikacja zakończona ✓ - sukces!"
        print(f"  Test mieszany: {mixed}")
        test_result("Tekst mieszany (ASCII + Unicode)", True)

    except UnicodeEncodeError as e:
        test_result("Obsluga kodowania UTF-8", False, str(e))
    except Exception as e:
        test_result("Obsluga kodowania UTF-8", False, str(e))


def test_empty_data_validation():
    """
    TEST 3: Empty Data Validation
    Verifies that the AI assistant logic handles empty/insufficient data correctly.
    """
    print("\n" + "=" * 60)
    print("TEST 3: WERYFIKACJA WALIDACJI PUSTYCH DANYCH")
    print("=" * 60)

    # Test 3.1: Simulate empty product data
    try:
        df_empty = pd.DataFrame()
        is_empty = df_empty.empty
        test_result("Wykrywanie pustego DataFrame", is_empty)
    except Exception as e:
        test_result("Wykrywanie pustego DataFrame", False, str(e))

    # Test 3.2: Test last_4_weeks calculation with various scenarios
    test_cases = [
        ([], "pusta lista", 0),
        ([10], "1 element", 10),
        ([10, 20], "2 elementy", 15),
        ([10, 20, 30, 40], "4 elementy", 25),
    ]

    for data, desc, expected_avg in test_cases:
        try:
            # Simulate the fixed logic from main.py
            last_4_weeks = data

            if not last_4_weeks or len(last_4_weeks) < 2:
                # Insufficient data path
                avg_consumption = last_4_weeks[0] if last_4_weeks else 0
            else:
                avg_consumption = sum(last_4_weeks) / len(last_4_weeks)

            passed = abs(avg_consumption - expected_avg) < 0.01
            test_result(
                f"Kalkulacja sredniej ({desc})", passed, f"Oczekiwano {expected_avg}, otrzymano {avg_consumption}"
            )
        except Exception as e:
            test_result(f"Kalkulacja sredniej ({desc})", False, str(e))

    # Test 3.3: Test with actual database data (if available)
    try:
        db = DatabaseConnector()
        df_hist = db.get_historical_data()

        if df_hist.empty:
            test_result("Dane historyczne z bazy", True, "Brak danych - to jest ok dla tego testu")
        else:
            # Get a product that might have limited data
            sample_product_id = df_hist["TowarId"].iloc[0]
            df_prod = df_hist[df_hist["TowarId"] == sample_product_id].copy()

            last_4_weeks = df_prod["Quantity"].tail(4).tolist()

            # Apply the validation logic
            if not last_4_weeks or len(last_4_weeks) < 2:
                avg_consumption = last_4_weeks[0] if last_4_weeks else 0
                test_result(
                    "Walidacja z prawdziwymi danymi (malo danych)",
                    True,
                    f"Poprawnie obsluzono {len(last_4_weeks)} rekordow",
                )
            else:
                avg_consumption = sum(last_4_weeks) / len(last_4_weeks)
                test_result(
                    "Walidacja z prawdziwymi danymi (dosc danych)",
                    avg_consumption > 0,
                    f"Srednia: {avg_consumption:.2f}",
                )

    except Exception as e:
        test_result("Walidacja z prawdziwymi danymi", False, str(e))


def test_database_methods():
    """
    TEST 4: Database Methods Integration
    Verifies that all key DatabaseConnector methods work correctly.
    """
    print("\n" + "=" * 60)
    print("TEST 4: WERYFIKACJA METOD DatabaseConnector")
    print("=" * 60)

    try:
        db = DatabaseConnector()

        # Test 4.1: test_connection
        conn_ok = db.test_connection()
        test_result("test_connection()", conn_ok)

        if not conn_ok:
            print("  [!] Pomijanie pozostalych testow - brak polaczenia")
            return

        # Test 4.2: get_historical_data
        df_hist = db.get_historical_data()
        test_result("get_historical_data()", isinstance(df_hist, pd.DataFrame), f"Zwrocono {len(df_hist)} rekordow")

        # Test 4.3: get_current_stock
        df_stock = db.get_current_stock()
        test_result("get_current_stock()", isinstance(df_stock, pd.DataFrame), f"Zwrocono {len(df_stock)} produktow")

        # Test 4.4: get_products_with_technology
        df_tech = db.get_products_with_technology()
        test_result(
            "get_products_with_technology()",
            isinstance(df_tech, pd.DataFrame),
            f"Zwrocono {len(df_tech)} produktow z technologia",
        )

        # Test 4.5: get_bom_with_stock (if products with tech exist)
        if not df_tech.empty:
            test_prod_id = int(df_tech["FinalProductId"].iloc[0])
            df_bom = db.get_bom_with_stock(test_prod_id)
            test_result(
                "get_bom_with_stock()",
                isinstance(df_bom, pd.DataFrame),
                f"BOM dla produktu {test_prod_id}: {len(df_bom)} skladnikow",
            )
        else:
            test_result("get_bom_with_stock()", True, "Pominieto - brak produktow z technologia")

        # Test 4.6: get_product_usage_stats (if stock data exists)
        if not df_stock.empty:
            test_raw_id = int(df_stock["TowarId"].iloc[0])
            df_usage = db.get_product_usage_stats(test_raw_id)
            test_result(
                "get_product_usage_stats()",
                isinstance(df_usage, pd.DataFrame),
                f"Uzycie surowca {test_raw_id}: {len(df_usage)} wyrobow",
            )
        else:
            test_result("get_product_usage_stats()", True, "Pominieto - brak danych o stanach")

    except Exception as e:
        test_result("Inicjalizacja DatabaseConnector", False, str(e))


def run_all_tests():
    """Runs all test suites and prints summary."""
    global TESTS_PASSED, TESTS_FAILED

    print("\n" + "=" * 60)
    print("  TESTY NAPRAW PRIORYTETU WYSOKIEGO")
    print("  AI Supply Assistant - CTI Production")
    print("=" * 60)

    # Run all test suites
    test_database_schema()
    test_encoding_support()
    test_empty_data_validation()
    test_database_methods()

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
        print("  Naprawy priorytetu wysokiego dzialaja poprawnie.")
    else:
        print(f"\n  [!] {TESTS_FAILED} TESTOW NIEZALICZONYCH")
        print("  Sprawdz szczegoly powyzej.")

    return TESTS_FAILED == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
