"""
Comprehensive verification of ZP (Production Orders) - TH (Technology) - BOM relations
in the CTI Production module database.
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


def run_verification():
    print("=" * 60)
    print("WERYFIKACJA RELACJI ZP-TH-BOM (CTI DATABASE)")
    print("=" * 60)

    try:
        db = DatabaseConnector()
        print("[OK] Polaczenie z baza: OK\n")
    except Exception as e:
        print(f"[BLAD] Blad polaczenia: {e}")
        return

    # 1. Check CtiZlecenieNag (ZP - Production Orders) structure
    print("--- 1. STRUKTURA CtiZlecenieNag (Zlecenia Produkcyjne ZP) ---")
    q1 = """
    SELECT
        COUNT(*) as TotalZP,
        SUM(CASE WHEN CZN_CTNId IS NOT NULL AND CZN_CTNId > 0 THEN 1 ELSE 0 END) as WithTechnology,
        SUM(CASE WHEN CZN_TwrId IS NOT NULL AND CZN_TwrId > 0 THEN 1 ELSE 0 END) as WithProduct
    FROM dbo.CtiZlecenieNag
    """
    df1 = db.execute_query(q1)
    print(df1.to_string(index=False))
    total_zp = df1["TotalZP"].iloc[0] if not df1.empty else 0

    # 2. Check CtiTechnolNag (TH - Technologies) structure
    print("\n--- 2. STRUKTURA CtiTechnolNag (Technologie TH) ---")
    q2 = """
    SELECT
        COUNT(*) as TotalTH,
        SUM(CASE WHEN CTN_Status > 0 THEN 1 ELSE 0 END) as ActiveTH,
        SUM(CASE WHEN CTN_TwrId IS NOT NULL AND CTN_TwrId > 0 THEN 1 ELSE 0 END) as WithProduct
    FROM dbo.CtiTechnolNag
    """
    df2 = db.execute_query(q2)
    print(df2.to_string(index=False))
    total_th = df2["TotalTH"].iloc[0] if not df2.empty else 0

    # 3. Check CtiTechnolElem (Tech Elements - BOM items)
    print("\n--- 3. STRUKTURA CtiTechnolElem (Elementy Technologii - BOM) ---")
    q3 = """
    SELECT
        CTE_Typ as Typ,
        CASE CTE_Typ
            WHEN 1 THEN 'Surowiec z cecha'
            WHEN 2 THEN 'Surowiec'
            WHEN 3 THEN 'Odpad'
            WHEN 4 THEN 'Usluga/Kooperacja'
            ELSE 'Inny'
        END as Opis,
        COUNT(*) as Ilosc
    FROM dbo.CtiTechnolElem
    GROUP BY CTE_Typ
    ORDER BY CTE_Typ
    """
    df3 = db.execute_query(q3)
    print(df3.to_string(index=False))

    # 4. Verify ZP <-> TH relationship
    print("\n--- 4. WERYFIKACJA RELACJI ZP -> TH ---")
    q4 = """
    SELECT TOP 5
        zp.CZN_ID as ZP_ID,
        zp.CZN_NrPelny as ZP_Numer,
        zp.CZN_CTNId as TH_ID,
        th.CTN_Numer as TH_Numer,
        t.Twr_Kod as ProduktKod
    FROM dbo.CtiZlecenieNag zp
    LEFT JOIN dbo.CtiTechnolNag th ON zp.CZN_CTNId = th.CTN_ID
    LEFT JOIN CDN.Towary t ON zp.CZN_TwrId = t.Twr_TwrId
    WHERE zp.CZN_CTNId IS NOT NULL AND zp.CZN_CTNId > 0
    ORDER BY zp.CZN_ID DESC
    """
    df4 = db.execute_query(q4)
    if not df4.empty:
        print("Przykladowe polaczenia ZP -> TH:")
        print(df4.to_string(index=False))
    else:
        print("UWAGA: Brak zlecen z przypisana technologia!")

    # 5. Verify BOM for a sample product with technology
    print("\n--- 5. PRZYKLADOWY BOM DLA WYROBU Z TECHNOLOGIA ---")
    q5 = """
    SELECT TOP 1
        CTN_TwrId as FinalProductId,
        CTN_ID as TH_ID,
        t.Twr_Kod as ProductCode,
        t.Twr_Nazwa as ProductName
    FROM dbo.CtiTechnolNag n
    JOIN CDN.Towary t ON n.CTN_TwrId = t.Twr_TwrId
    WHERE CTN_TwrId IS NOT NULL AND CTN_TwrId > 0
    """
    df5 = db.execute_query(q5)
    df_tech_prods = pd.DataFrame()  # Initialize

    if not df5.empty:
        final_id = df5["FinalProductId"].iloc[0]
        th_id = df5["TH_ID"].iloc[0]
        print(f"Wyrob: {df5['ProductName'].iloc[0]} ({df5['ProductCode'].iloc[0]})")
        print(f"TH ID: {th_id}\n")

        # Get BOM for this TH
        q_bom = f"""
        SELECT TOP 10
            e.CTE_Lp as Lp,
            t.Twr_Kod as SurowiecKod,
            e.CTE_Ilosc as Ilosc,
            t.Twr_JM as JM,
            CASE e.CTE_Typ
                WHEN 1 THEN 'Sur+Cecha'
                WHEN 2 THEN 'Surowiec'
                WHEN 3 THEN 'Odpad'
                WHEN 4 THEN 'Usluga'
            END as Typ
        FROM dbo.CtiTechnolElem e
        JOIN CDN.Towary t ON e.CTE_TwrId = t.Twr_TwrId
        WHERE e.CTE_CTNId = {th_id}
        ORDER BY e.CTE_Lp
        """
        df_bom = db.execute_query(q_bom)
        if not df_bom.empty:
            print("BOM (Lista Materialowa):")
            print(df_bom.to_string(index=False))
        else:
            print("Brak elementow w technologii.")
    else:
        print("Brak technologii w bazie.")

    # 6. Verify get_products_with_technology method
    print("\n--- 6. WERYFIKACJA METODY get_products_with_technology ---")
    try:
        df_tech_prods = db.get_products_with_technology()
        print(f"Liczba wyrobow z technologia: {len(df_tech_prods)}")
        if not df_tech_prods.empty:
            print("\nPierwszych 5 wyrobow z technologia:")
            print(df_tech_prods.head().to_string(index=False))
    except Exception as e:
        print(f"Blad: {e}")

    # 7. Verify get_bom_with_stock method
    print("\n--- 7. WERYFIKACJA METODY get_bom_with_stock ---")
    try:
        if not df_tech_prods.empty:
            sample_id = int(df_tech_prods["FinalProductId"].iloc[0])
            df_bom_stock = db.get_bom_with_stock(sample_id)
            print(f"BOM ze stanami dla produktu ID={sample_id}:")
            if not df_bom_stock.empty:
                print(df_bom_stock.to_string(index=False))
            else:
                print("Brak surowcow w BOM dla tego produktu.")
    except Exception as e:
        print(f"Blad: {e}")

    # 8. Verify CtiZlecenieElem (ZP elements - actual raw material usage)
    print("\n--- 8. WERYFIKACJA CtiZlecenieElem (Zuzycie surowcow na ZP) ---")
    q8 = """
    SELECT TOP 5
        n.CZN_ID as ZP_ID,
        n.CZN_NrPelny as ZP_Numer,
        t.Twr_Kod as SurowiecKod,
        e.CZE_Ilosc as Ilosc
    FROM dbo.CtiZlecenieElem e
    JOIN dbo.CtiZlecenieNag n ON e.CZE_CZNId = n.CZN_ID
    JOIN CDN.Towary t ON e.CZE_TwrId = t.Twr_TwrId
    WHERE e.CZE_Typ IN (1, 2)
    ORDER BY n.CZN_ID DESC
    """
    df8 = db.execute_query(q8)
    if not df8.empty:
        print(df8.to_string(index=False))
    else:
        print("Brak danych o zuzyciu surowcow.")

    # 9. Final summary
    print("\n" + "=" * 60)
    print("PODSUMOWANIE WERYFIKACJI")
    print("=" * 60)
    print("[OK] Polaczenie z baza: OK")
    print(f"[OK] Zlecenia produkcyjne (ZP): {total_zp}")
    print(f"[OK] Technologie (TH): {total_th}")
    print(f"[OK] Wyroby z technologia (AI mode): {len(df_tech_prods) if not df_tech_prods.empty else 0}")
    print("\nRelacje kluczowe:")
    print("  CtiZlecenieNag.CZN_CTNId -> CtiTechnolNag.CTN_ID (ZP -> TH)")
    print("  CtiTechnolNag.CTN_TwrId -> CDN.Towary.Twr_TwrId (TH -> Wyrob)")
    print("  CtiTechnolElem.CTE_CTNId -> CtiTechnolNag.CTN_ID (BOM -> TH)")


if __name__ == "__main__":
    run_verification()
