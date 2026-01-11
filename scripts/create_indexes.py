"""
Database Index Management Script
=================================
Creates recommended indexes for optimal performance of the AI Supply Assistant.

WARNING: Creating indexes may take time on large tables and temporarily lock them.
Run this script during low-activity periods.

Usage:
    python scripts/create_indexes.py --check     # Check which indexes exist/missing
    python scripts/create_indexes.py --create    # Create missing indexes
    python scripts/create_indexes.py --drop      # Drop all recommended indexes (rollback)
"""
import argparse
import io
import os
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from src.db_connector import DatabaseConnector

# Index definitions
RECOMMENDED_INDEXES = [
    {
        "name": "IX_CtiZlecenieElem_TwrId_Typ",
        "table": "dbo.CtiZlecenieElem",
        "columns": "CZE_TwrId, CZE_Typ",
        "create_sql": "CREATE NONCLUSTERED INDEX IX_CtiZlecenieElem_TwrId_Typ ON dbo.CtiZlecenieElem(CZE_TwrId, CZE_Typ)",
        "drop_sql": "DROP INDEX IF EXISTS IX_CtiZlecenieElem_TwrId_Typ ON dbo.CtiZlecenieElem",
        "reason": "Optymalizuje filtrowanie surowcow (CZE_Typ IN (1,2)) - uzywane w get_historical_data, get_current_stock",
    },
    {
        "name": "IX_CtiZlecenieNag_DataRealizacji",
        "table": "dbo.CtiZlecenieNag",
        "columns": "CZN_DataRealizacji",
        "create_sql": "CREATE NONCLUSTERED INDEX IX_CtiZlecenieNag_DataRealizacji ON dbo.CtiZlecenieNag(CZN_DataRealizacji) INCLUDE (CZN_ID, CZN_TwrId)",
        "drop_sql": "DROP INDEX IF EXISTS IX_CtiZlecenieNag_DataRealizacji ON dbo.CtiZlecenieNag",
        "reason": "Optymalizuje zapytania historyczne po dacie realizacji - uzywane w get_historical_data",
    },
    {
        "name": "IX_CtiTechnolElem_CTNId",
        "table": "dbo.CtiTechnolElem",
        "columns": "CTE_CTNId",
        "create_sql": "CREATE NONCLUSTERED INDEX IX_CtiTechnolElem_CTNId ON dbo.CtiTechnolElem(CTE_CTNId) INCLUDE (CTE_TwrId, CTE_Ilosc, CTE_Typ)",
        "drop_sql": "DROP INDEX IF EXISTS IX_CtiTechnolElem_CTNId ON dbo.CtiTechnolElem",
        "reason": "Optymalizuje pobieranie BOM dla technologii - uzywane w get_bom_with_stock, get_product_bom",
    },
    {
        "name": "IX_CtiTechnolNag_TwrId",
        "table": "dbo.CtiTechnolNag",
        "columns": "CTN_TwrId",
        "create_sql": "CREATE NONCLUSTERED INDEX IX_CtiTechnolNag_TwrId ON dbo.CtiTechnolNag(CTN_TwrId) INCLUDE (CTN_ID)",
        "drop_sql": "DROP INDEX IF EXISTS IX_CtiTechnolNag_TwrId ON dbo.CtiTechnolNag",
        "reason": "Optymalizuje wyszukiwanie technologii dla produktu - uzywane w get_products_with_technology",
    },
    {
        "name": "IX_CtiZlecenieElem_CZNId",
        "table": "dbo.CtiZlecenieElem",
        "columns": "CZE_CZNId",
        "create_sql": "CREATE NONCLUSTERED INDEX IX_CtiZlecenieElem_CZNId ON dbo.CtiZlecenieElem(CZE_CZNId) INCLUDE (CZE_TwrId, CZE_Ilosc, CZE_Typ)",
        "drop_sql": "DROP INDEX IF EXISTS IX_CtiZlecenieElem_CZNId ON dbo.CtiZlecenieElem",
        "reason": "Optymalizuje JOIN z CtiZlecenieNag - uzywane w wielu zapytaniach",
    },
]


def check_existing_indexes(db: DatabaseConnector) -> set:
    """Returns set of existing index names from the recommended list."""
    index_names = [idx["name"] for idx in RECOMMENDED_INDEXES]
    placeholders = ", ".join([f"'{name}'" for name in index_names])

    query = f"""
    SELECT i.name as IndexName, t.name as TableName
    FROM sys.indexes i
    JOIN sys.tables t ON i.object_id = t.object_id
    WHERE i.name IN ({placeholders})
    """

    try:
        df = db.execute_query(query, query_name="check_indexes")
        if not df.empty:
            return set(df["IndexName"].tolist())
    except Exception as e:
        print(f"[BLAD] Nie mozna sprawdzic indeksow: {e}")

    return set()


def print_index_status(existing: set):
    """Prints status of all recommended indexes."""
    print("\n" + "=" * 70)
    print("STATUS REKOMENDOWANYCH INDEKSOW")
    print("=" * 70)

    for idx in RECOMMENDED_INDEXES:
        status = "[OK] ISTNIEJE" if idx["name"] in existing else "[--] BRAK"
        print(f"\n{status}: {idx['name']}")
        print(f"    Tabela:  {idx['table']}")
        print(f"    Kolumny: {idx['columns']}")
        print(f"    Powod:   {idx['reason']}")

    print("\n" + "-" * 70)
    print(f"Podsumowanie: {len(existing)}/{len(RECOMMENDED_INDEXES)} indeksow istnieje")
    print("=" * 70)


def create_indexes(db: DatabaseConnector, existing: set, dry_run: bool = False):
    """Creates missing indexes."""
    missing = [idx for idx in RECOMMENDED_INDEXES if idx["name"] not in existing]

    if not missing:
        print("\n[OK] Wszystkie rekomendowane indeksy juz istnieja!")
        return

    print(f"\n[INFO] Tworzenie {len(missing)} brakujacych indeksow...")

    for idx in missing:
        print(f"\n  Tworzenie: {idx['name']}...")

        if dry_run:
            print(f"    [DRY-RUN] SQL: {idx['create_sql']}")
            continue

        try:
            with db.engine.connect() as conn:
                conn.execute(text(idx["create_sql"]))
                conn.commit()
            print("    [OK] Utworzono pomyslnie")
        except Exception as e:
            print(f"    [BLAD] {e}")


def drop_indexes(db: DatabaseConnector, existing: set, dry_run: bool = False):
    """Drops existing recommended indexes (rollback)."""
    to_drop = [idx for idx in RECOMMENDED_INDEXES if idx["name"] in existing]

    if not to_drop:
        print("\n[INFO] Brak indeksow do usuniecia.")
        return

    print(f"\n[UWAGA] Usuwanie {len(to_drop)} indeksow...")

    for idx in to_drop:
        print(f"\n  Usuwanie: {idx['name']}...")

        if dry_run:
            print(f"    [DRY-RUN] SQL: {idx['drop_sql']}")
            continue

        try:
            with db.engine.connect() as conn:
                conn.execute(text(idx["drop_sql"]))
                conn.commit()
            print("    [OK] Usunieto pomyslnie")
        except Exception as e:
            print(f"    [BLAD] {e}")


def main():
    parser = argparse.ArgumentParser(description="Zarzadzanie indeksami bazy danych AI Supply Assistant")
    parser.add_argument("--check", action="store_true", help="Sprawdz status indeksow")
    parser.add_argument("--create", action="store_true", help="Utworz brakujace indeksy")
    parser.add_argument("--drop", action="store_true", help="Usun rekomendowane indeksy (rollback)")
    parser.add_argument("--dry-run", action="store_true", help="Tylko pokaz SQL bez wykonywania")

    args = parser.parse_args()

    # Default to --check if no action specified
    if not (args.check or args.create or args.drop):
        args.check = True

    print("\n" + "=" * 70)
    print("  ZARZADZANIE INDEKSAMI - AI Supply Assistant")
    print("=" * 70)

    try:
        db = DatabaseConnector(enable_diagnostics=False)
        print("[OK] Polaczenie z baza danych")
    except Exception as e:
        print(f"[BLAD] Nie mozna polaczyc z baza: {e}")
        sys.exit(1)

    existing = check_existing_indexes(db)

    if args.check:
        print_index_status(existing)

    if args.create:
        create_indexes(db, existing, dry_run=args.dry_run)
        if not args.dry_run:
            print("\n[INFO] Sprawdzanie po utworzeniu...")
            existing = check_existing_indexes(db)
            print_index_status(existing)

    if args.drop:
        confirm = input("\n[UWAGA] Czy na pewno chcesz usunac indeksy? (tak/nie): ")
        if confirm.lower() == "tak":
            drop_indexes(db, existing, dry_run=args.dry_run)
            if not args.dry_run:
                print("\n[INFO] Sprawdzanie po usunieciu...")
                existing = check_existing_indexes(db)
                print_index_status(existing)
        else:
            print("[INFO] Anulowano.")


if __name__ == "__main__":
    main()
