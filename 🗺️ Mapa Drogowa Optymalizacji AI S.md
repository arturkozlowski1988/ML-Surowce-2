# 🗺️ Mapa Drogowa Rozwoju: AI Supply Assistant (v2.0)

> **Status Projektu**: Wersja 1.4.0 (Stabilna)  
> **Data Aktualizacji**: Styczeń 2026 (Symulacja) / Realny Czas: Q1 2025  
> **Cel**: Transformacja z narzędzia analitycznego w aktywnego asystenta operacyjnego.

---

## 1. Podsumowanie Audytu (Stan Obecny v1.4.0)

Po weryfikacji kodu źródłowego (`main.py`, `src/security`, `src/db_connector`) zidentyfikowano następujący status:

### ✅ Zrealizowane (Done)

* **Bezpieczeństwo**: Wdrożono RBAC (Role-Based Access Control) i haszowanie haseł.
* **Konfiguracja**: Walidacja Pydantic i usuwanie hardcoded credentials.
* **Baza Danych**: Diagnostyka zapytań i caching wyników.
* **GUI**: Modułowa struktura widoków i kreator połączenia.

### ⚠️ Dług Techniczny (To Do)

* **Wydajność**: Synchroniczne wywołania blokują interfejs Streamlit (szczególnie przy zapytaniach AI/SQL).
* **Bezpieczeństwo Danych**: Użycie `NOLOCK` przy odczycie stanów bieżących (ryzyko brudnych odczytów).
* **Skalowalność**: Pętla `for` w module prognozowania (`forecasting.py`) przy dużej liczbie indeksów.

---

## 2. Harmonogram Wdrożeń

### Faza 1: Fundament Techniczny i Wydajność (Q1 2025)

*Cel: Zapewnienie płynności działania aplikacji przy rosnącym wolumenie danych.*

#### 1.1 Asynchroniczność (AsyncIO) `[PRIORYTET: WYSOKI]`

- [ ] **Migracja SQL**: Implementacja asynchronicznego ładowania danych (`async/await` lub `concurrent.futures`) w `AsyncDataLoader`.
* [ ] **Non-blocking GUI**: Dodanie spinnerów i pasków postępu, które nie zamrażają okna przeglądarki.
* [ ] **AI Client**: Asynchroniczne odpytywanie API Gemini/Ollama.

#### 1.2 Optymalizacja Silnika Prognoz (`src/forecasting.py`)

- [ ] **Równoległość**: Zastąpienie pętli sekwencyjnej przetwarzaniem równoległym (`joblib` lub `multiprocessing`).
* [ ] **Kalendarz**: Dodanie biblioteki `holidays` (PL) do features modelu (lepsze wykrywanie sezonowości).

#### 1.3 Bezpieczeństwo i Logi

- [ ] **Poprawa SQL**: Zamiana `WITH (NOLOCK)` na `READ COMMITTED SNAPSHOT` dla zapytań o stany magazynowe (`get_current_stock`).
* [ ] **File Logging**: Skonfigurowanie `RotatingFileHandler` do zapisywania błędów krytycznych w plikach (dla celów audytu).
* [ ] **Zarządzanie Połączeniem**: Implementacja `engine.dispose()` przy przełączaniu baz danych w `main.py`, aby zwalniać zasoby.

---

### Faza 2: Funkcjonalność Biznesowa - MRP Lite (Q2 2025)

*Cel: Dostarczenie narzędzi bezpośrednio wspierających decyzje zakupowe.*

#### 2.1 Symulator Produkcji (BOM Analysis)

- [ ] **Drzewo Produktu**: Rekurencyjna analiza BOM (`get_product_bom`) w dół.
* [ ] **Symulacja**: Funkcja "Co-If" – *Czy mam surowce, aby wyprodukować 500 szt. wyrobu X na przyszły tydzień?*
* [ ] **Wizualizacja Braków**: Tabela kolorująca brakujące składniki na czerwono.

#### 2.2 Inteligentne Alerty (Smart Alerts)

- [ ] **Dashboard**: Widok "Krytyczne Braki" oparty na logice:
  `Stan Obecny - Rezerwacje + W Drodze < Minimum Logistyczne`.
* [ ] **Wyjaśnianie AI**: Integracja LLM do wyjaśniania przyczyn (np. "Nagły skok zużycia w zeszłym miesiącu").

#### 2.3 Ocena Dostawców (Vendor Rating)

- [ ] **Analiza Opóźnień**: Wyliczanie średniego opóźnienia dostaw na podstawie historii (`CDN.TraNag`).
* [ ] **Rekomendacje**: Sugerowanie bezpieczniejszego dostawcy przy zamówieniach krytycznych.

---

### Faza 3: Integracja i Automatyzacja (Q3 2025)

*Cel: Zamknięcie pętli operacyjnej (od analizy do działania).*

#### 3.1 Generowanie Zamówień (Write-Back)

- [ ] **Brudnopis Zamówienia**: Generowanie dokumentów ZZ w buforze Optimy (`CDN.TraNag` / `CDN.TraElem`).
* [ ] **Walidacja**: Implementacja ścisłych reguł walidacji przed `INSERT` (aby nie uszkodzić spójności ERP).

#### 3.2 Raportowanie BI

- [ ] **Eksport Danych**: Automatyczny zrzut prognoz do formatu dostępnego dla Power BI / Excel (np. widok SQL lub CSV).
* [ ] **Raport Zarządczy**: Wizualizacja KPI (Skuteczność prognoz, Wartość stanów nadmiernych).

---

## 3. Metryki Sukcesu (KPI)

| Obszar | Metryka Obecna | Cel (Q3 2025) |
| :--- | :--- | :--- |
| **Wydajność** | Czas ładowania analizy > 5s | < 2s (dzięki AsyncIO) |
| **Prognozowanie** | Czas treningu (100 SKU) > 30s | < 10s (Multiprocessing) |
| **Operacje** | Czas weryfikacji braków ~30 min | < 5 min (Dashboard MRP) |
| **Stabilność** | Okazjonalne "zamrożenia" GUI | 99.9% responsywności |

---

## 4. Wymagane Zasoby i Stack

* **Backend**: Python 3.11+
* **Baza Danych**: MS SQL Server 2019 (Test & Prod)
* **Biblioteki Kluczowe**: `streamlit`, `sqlalchemy`, `pandas`, `scikit-learn`, `joblib`, `holidays`.
* **AI**: Google Gemini 2.0 Flash / Ollama (Llama 3).

> *Zatwierdzono do realizacji przez Zespół Deweloperski.*
