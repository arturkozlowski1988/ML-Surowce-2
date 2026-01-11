# Raport z Inspekcji Kodu i Architektury

**Data:** 2026-01-11
**Repozytorium:** ML-Surowce-2
**Autor:** Antigravity (AI Senior Python/MSSQL Developer)

---

## 1. Zakres i Założenia

Przeanalizowano główny kod źródłowy aplikacji znajdujący się w katalogu `src/`, konfigurację w `config/` oraz skrypty pomocnicze w `scripts/`.

**Elementy zweryfikowane:**

- Architektura i podział na warstwy.
- Statyczna analiza kodu (manualna symulacja narzędzi Ruff/Bandit).
- Warstwa dostępu do danych (MSSQL - `src/db_connector.py`).
- Bezpieczeństwo (zarządzanie sekretami, SQL Injection).
- Pokrycie testami.

**Czego nie zweryfikowano:**

- Działania aplikacji w środowisku produkcyjnym (brak dostępu do żywej bazy danych).
- Pełnej poprawności logiki biznesowej (brak specyfikacji wymagań).

---

## 2. Najważniejsze Ryzyka

### 🔴 Critical (Krytyczne)

- **Brak ustandaryzowanych testów automatycznych:** Projekt polega na ad-hoc skryptach w `scripts/` (np. `test_security.py`). Brak frameworka `pytest` i ciągłej integracji (CI) zwiększa ryzyko regresji przy każdej zmianie.

### 🟠 High (Wysokie)

- **Złożoność `src/db_connector.py`:** Plik ten pełni rolę "Boskiego Obiektu" dla bazy danych (>1700 linii). Miesza logikę połączenia, cache'owania, diagnostyki i dziesiątki zapytań SQL. Utrudnia to utrzymanie i testowanie.
- **Nadużywanie `WITH (NOLOCK)`:** Większość zapytań używa `NOLOCK`. Choć poprawia to wydajność (nie blokuje tabel), niesie ryzyko "brudnych odczytów" (dirty reads) - raporty mogą pokazywać niespójne dane w trakcie trwania transakcji zapisu.

### 🟡 Medium (Średnie)

- **Konstrukcja SQL przez konkatenację stringów:** Choć parametry są przekazywane bezpiecznie (`params={...}`), sama struktura zapytań jest budowana dynamicznie (np. `base_query += " AND ..."`). Jest to podatne na błędy logiczne.
- **Brak lintera/formatera w CI:** Kod jest czytelny, ale brak automatycznego wymuszania stylu (Ruff/Black) doprowadzi do długu technologicznego.

---

## 3. Szczegółowa Lista Problemów

### Python & Architektura

| Plik / Moduł | Typ | Opis |
|--------------|-----|------|
| `src/db_connector.py` | Design | Klasa `DatabaseConnector` jest zbyt duża. Powinna zostać rozbita na mniejsze repozytoria (np. `ProductRepository`, `OrderRepository`). |
| `src/config_manager.py` | Security | Plik ten jest dobrze napisany, ale należy uważać, by `config/app_settings.json` nie trafił do repozytorium z prawdziwymi kluczami (obecnie są puste stringi - OK). |
| `scripts/` | Quality | Duża ilość "martwych" lub tymczasowych skryptów testowych (np. w `scripts/archive/`). |
| Cały projekt | Tooling | Brak pliku `pyproject.toml` lub `.pre-commit-config.yaml` definiującego standardy kodu. |

### MSSQL (T-SQL)

| Query Name | Ryzyko | Opis |
|------------|--------|------|
| `get_historical_data` | Performance | Zapytanie agreguje duże ilości danych. Użycie `NOLOCK` jest tu uzasadnione wydajnością, ale warto rozważyć dedykowany widok zmaterializowany lub tabelę raportową. |
| `get_bom_with_warehouse_breakdown` | Complexity | Skomplikowany `JOIN` i `WITH` (CTE). Trudne do debugowania. |
| Indeksowanie | Optimization | Klasa ma metodę `check_and_create_indexes`, co jest dobrą praktyką, ale sugerowane indeksy powinny być wdrożone w bazie, a nie tylko sprawdzane w kodzie aplikacji. |

---

## 4. Rekomendacje Optymalizacji

### "Quick Wins" (Do zrobienia natychmiast)

1. **Zainstaluj Ruff:** Dodaj `ruff` do `requirements.txt` i uruchom `ruff check . --fix`, aby wyczyścić importy i drobne błędy.
2. **Skonsoliduj testy:** Przenieś wartościowe testy z `scripts/` do nowego katalogu `tests/` i uruchom je przez `pytest`.
3. **Weryfikacja Indeksów:** Uruchom metodę `check_and_create_indexes` na środowisku testowym i zaaplikuj brakujące indeksy (szczególnie `IX_CtiZlecenieElem_TwrId_Typ`).

### Długoterminowe

1. **Refaktor `DatabaseConnector`:** Wydziel metody do osobnych klas DAO/Repository (np. `src/database/repositories/orders.py`).
2. **Wprowadzenie Migracji:** Jeśli aplikacja zarządza schematem (tworzy tabele/indeksy), użyj narzędzia takiego jak `Alembic`.
3. **CI/CD:** Skonfiguruj GitHub Actions lub Azure DevOps do uruchamiania testów i lintera przy każdym Pull Request.

---

## 5. Proponowane Zmiany (Przykład Refaktora)

**Problem:** `DatabaseConnector` jest przeładowany.
**Propozycja:** Wydzielenie logiki zapytań produkcyjnych.

```python
# src/repositories/production_repository.py

class ProductionRepository:
    def __init__(self, db_connector):
        self.db = db_connector

    def get_active_orders_demand(self, product_ids=None, exclude_completed=True):
        # ... logic moved from DatabaseConnector ...
        query = "..."
        return self.db.execute_query(query, params=...)
```

**Diff w `src/db_connector.py`:**

```diff
-    def get_active_orders_demand(self, product_ids: list = None, exclude_completed: bool = True) -> pd.DataFrame:
-        # ... 50 lines of code ...
+    # Metody przeniesione do ProductionRepository
```

---

## 6. Polecane Narzędzia

1. **Ruff:** Wszystko-w-jędnym linter i formatter (zastępuje Flake8, Black, isort). Bardzo szybki.
2. **Pytest:** Standard przemysłowy do testowania.
3. **Pre-commit:** Narzędzie do uruchamiania sprawdzania kodu przed commitem.

### Konfiguracja `.pre-commit-config.yaml` (Rekomendowana)

```yaml
repos:
-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
    -   id: ruff
    -   id: ruff-format
```

---

## Następne Kroki

1. [ ] Utworzyć katalog `tests/` i przenieść tam logikę z `scripts/test_*.py`.
2. [ ] Dodać `ruff` do projektu i poprawić automatycznie błędy (`ruff check . --fix`).
3. [ ] Przeprowadzić refaktor `DatabaseConnector` - wydzielić jedną domenę (np. Produkcja) do osobnego serwisu/repozytorium jako Proof of Concept.
4. [ ] Przeanalizować zasadność `WITH (NOLOCK)` w raportach finansowych (jeśli takie dojdą) - tam spójność jest ważniejsza niż wydajność.
