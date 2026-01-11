# Dokumentacja Techniczna: AI Supply Assistant

> **Wersja**: 1.5.0
> **Data aktualizacji**: 2026-01-10
> **System**: ERP Comarch Optima / Produkcja by CTI
> **Środowisko**: Python 3.9+, MS SQL Server, Streamlit

---

## Spis Treści

1. [Przegląd Architektury](#przegląd-architektury)
2. [Moduły Systemu](#moduły-systemu)
3. [Baza Danych - Schemat SQL](#baza-danych---schemat-sql)
4. [Moduł DatabaseConnector](#moduł-databaseconnector)
5. [Silniki AI](#silniki-ai)
6. [Moduły Machine Learning](#moduły-machine-learning)
7. [Bezpieczeństwo](#bezpieczeństwo)
8. [Architektura GUI](#architektura-gui)
9. [ViewModels (MVVM)](#viewmodels-mvvm)
10. [Usługi Asynchroniczne](#usługi-asynchroniczne)
11. [Deployment i Konfiguracja](#deployment-i-konfiguracja)
12. [Procedury Testowania](#procedury-testowania)

---

## Przegląd Architektury

### Wzorce Projektowe

Aplikacja wykorzystuje wzorzec **MVVM (Model-View-ViewModel)** w warstwie prezentacji:

- **Model**: DatabaseConnector, Forecaster, AI Clients
- **View**: GUI Components (Streamlit)
- **ViewModel**: AnalysisViewModel, PredictionViewModel (separacja logiki biznesowej od widoków)

### Stack Technologiczny

| Warstwa | Technologie |
|---------|-------------|
| **Frontend** | Streamlit 1.30+, Plotly (wykresy interaktywne) |
| **Backend** | Python 3.9+, SQLAlchemy (ORM) |
| **Baza Danych** | MS SQL Server (Comarch Optima/CDN) |
| **ML/AI** | scikit-learn, statsmodels, TensorFlow/Keras (LSTM), Google Gemini API, OpenRouter API (Access to 100+ models), Ollama, llama-cpp-python |
| **Model Management** | huggingface_hub (pobieranie modeli), joblib (persistence) |
| **Bezpieczeństwo** | python-dotenv, cryptography (Fernet), bcrypt, audit logging |

### Struktura Katalogów

```
ai-supply-assistant/
├── main.py                      # Entry point (Streamlit app)
├── src/
│   ├── db_connector.py          # Połączenie SQL + caching
│   ├── preprocessing.py         # Time series preprocessing
│   ├── forecasting.py           # ML models (RF, GB, ES)
│   ├── ai_engine/
│   │   ├── gemini_client.py     # Google Gemini API
│   │   ├── openrouter_client.py # OpenRouter API (Cloud)
│   │   ├── ollama_client.py     # Ollama local server
│   │   ├── local_llm.py         # Embedded LLM (llama-cpp)
│   │   └── anonymizer.py        # PII anonymization
│   ├── security/
│   │   ├── audit.py             # Security audit log
│   │   ├── encryption.py        # Config encryption (Fernet)
│   │   └── secrets_manager.py   # Secure secrets handling
│   ├── gui/
│   │   ├── components/          # Reusable UI components
│   │   │   ├── sidebar.py
│   │   │   ├── progress_indicators.py
│   │   │   └── responsive.py
│   │   └── views/               # Page views
│   │       ├── analysis.py      # Historical data analysis
│   │       ├── prediction.py    # Forecasting view
│   │       └── assistant.py     # AI assistant view
│   ├── viewmodels/              # MVVM ViewModels
│   │   ├── base_viewmodel.py
│   │   ├── analysis_viewmodel.py
│   │   └── prediction_viewmodel.py
│   └── services/
│       └── async_loader.py      # Async data loading
├── scripts/                     # Utility scripts (testing, debugging)
├── models/                      # LLM models (GGUF format)
└── requirements.txt
```

---

## Moduły Systemu

### 1. main.py - Entry Point

**Cel**: Inicjalizacja aplikacji Streamlit i routing między widokami.

**Parametry wejściowe**: Brak (konfiguracja z `.env`).

**Główne funkcje**:

- `main()`: Punkt wejścia aplikacji.
- `get_db_connection()`: Cached factory dla DatabaseConnector (singleton pattern via `@st.cache_resource`).

**Routing logika**:

```python
if app_mode == "Analiza Danych":
    render_analysis_view(...)
elif app_mode == "Predykcja":
    render_prediction_view(...)
elif app_mode == "AI Assistant (GenAI)":
    render_assistant_view(...)
```

**Zależności**:

- `src.db_connector.DatabaseConnector`
- `src.gui.views.*`
- `src.preprocessing`
- `src.forecasting.Forecaster`

---

## Baza Danych - Schemat SQL

### Źródło Danych: Comarch Optima / CTI Module

System integruje się z modułem produkcji **Produkcja by CTI** dla Comarch Optima.

### Kluczowe Tabele

#### 1. `dbo.CtiZlecenieNag` (Production Order Header)

Nagłówek zlecenia produkcyjnego.

| Kolumna | Typ | Opis |
|---------|-----|------|
| `CZN_ID` | INT (PK) | Identyfikator zlecenia |
| `CZN_TwrId` | INT (FK → Towary) | Wyrób gotowy (produkt finalny) |
| `CZN_DataRealizacji` | DATETIME | Data realizacji produkcji |
| `CZN_Status` | INT | Status zlecenia (1 = Aktywny) |

**Klauzula `NOLOCK`**: Używana w zapytaniach raportowych (read-only).

⚠️ **UWAGA**: `WITH (NOLOCK)` może odczytać niezcommitowane dane (dirty reads). Dopuszczalne w raportach, **NIE stosować w transakcjach modyfikujących dane**.

#### 2. `dbo.CtiZlecenieElem` (Production Order Elements)

Składniki wykorzystane w produkcji (surowce, materiały).

| Kolumna | Typ | Opis |
|---------|-----|------|
| `CZE_ID` | INT (PK) | Identyfikator elementu |
| `CZE_CZNId` | INT (FK → CtiZlecenieNag) | Powiązanie z nagłówkiem |
| `CZE_TwrId` | INT (FK → Towary) | Surowiec/materiał |
| `CZE_Ilosc` | DECIMAL(18,5) | Ilość zużyta |
| `CZE_Typ` | INT | Typ elementu (1,2 = Surowiec, 3 = Wyrób) |
| `CZE_Lp` | INT | Pozycja na liście |

**Filtrowanie surowców**: `CZE_Typ IN (1, 2)` - tylko materiały wejściowe.

#### 3. `dbo.CtiTechnolNag` (Technology Header)

Definicja technologii produkcji (BOM - Bill of Materials).

| Kolumna | Typ | Opis |
|---------|-----|------|
| `CTN_ID` | INT (PK) | Identyfikator technologii |
| `CTN_TwrId` | INT (FK → Towary) | Produkt finalny |
| `CTN_Status` | INT | Status technologii (1 = Aktywna) |
| `CTN_DataOd` | DATE | Data obowiązywania od |

#### 4. `dbo.CtiTechnolElem` (Technology Elements)

Składniki receptury (BOM).

| Kolumna | Typ | Opis |
|---------|-----|------|
| `CTE_ID` | INT (PK) | Identyfikator elementu |
| `CTE_CTNId` | INT (FK → CtiTechnolNag) | Powiązanie z technologią |
| `CTE_TwrId` | INT (FK → Towary) | Składnik (surowiec) |
| `CTE_Ilosc` | DECIMAL(18,5) | Ilość na jednostkę produktu |
| `CTE_Typ` | INT | Typ elementu (1,2 = Surowiec) |
| `CTE_Lp` | INT | Pozycja (kolejność) |

#### 5. `CDN.Towary` (Products Catalog)

Katalog produktów (zarówno wyroby gotowe jak i surowce).

| Kolumna | Typ | Opis |
|---------|-----|------|
| `Twr_TwrId` | INT (PK) | Identyfikator produktu |
| `Twr_Kod` | NVARCHAR(50) | Kod produktu (SKU) |
| `Twr_Nazwa` | NVARCHAR(255) | Nazwa produktu |
| `Twr_JM` | NVARCHAR(10) | Jednostka miary (kg, szt., m) |
| `Twr_Typ` | INT | Typ (0=Towar, 1=Usługa, 2=Usługa explicit) |

**Filtrowanie**: Wykluczenie usług: `Twr_Typ != 2`.

#### 6. `CDN.TwrZasoby` (Stock Levels)

Stany magazynowe.

| Kolumna | Typ | Opis |
|---------|-----|------|
| `TwZ_TwrId` | INT (FK → Towary) | Produkt |
| `TwZ_GIDNumer` | INT (FK → Magazyny) | Magazyn |
| `TwZ_Ilosc` | DECIMAL(18,5) | Ilość dostępna |

### Zalecane Indeksy

**Uwaga**: Poniższe indeksy **NIE są tworzone automatycznie** przez aplikację. Wymaga interwencji DBA.

```sql
-- Performance optimization indexes

-- 1. Index for raw material filtering
CREATE INDEX IX_CtiZlecenieElem_TwrId_Typ
ON dbo.CtiZlecenieElem(CZE_TwrId, CZE_Typ);
-- Reason: Przyspiesza filtrowanie surowców (CZE_Typ IN (1,2))

-- 2. Index for historical data date range queries
CREATE INDEX IX_CtiZlecenieNag_DataRealizacji
ON dbo.CtiZlecenieNag(CZN_DataRealizacji);
-- Reason: Przyspiesza zapytania z zakresem dat (get_historical_data)

-- 3. Index for technology elements lookup
CREATE INDEX IX_CtiTechnolElem_CTNId
ON dbo.CtiTechnolElem(CTE_CTNId);
-- Reason: Przyspiesza odczyt BOM (get_product_bom)

-- 4. Index for technology by product
CREATE INDEX IX_CtiTechnolNag_TwrId
ON dbo.CtiTechnolNag(CTN_TwrId);
-- Reason: Przyspiesza wyszukiwanie technologii dla produktu
```

**Weryfikacja indeksów**: Użyj funkcji `DatabaseConnector.check_and_create_indexes()`, która zwraca listę brakujących indeksów.

---

## Moduł DatabaseConnector

**Plik**: `src/db_connector.py`

### Cel Biznesowy

Centralna warstwa dostępu do danych SQL. Zapewnia:

- Połączenie pooling (wydajność)
- Query caching (TTL 5 min)
- Diagnostyka wydajności
- Audit logging (security)

### Parametry Inicjalizacji

```python
DatabaseConnector(
    enable_diagnostics: bool = True,  # Query performance logging
    enable_audit: bool = True          # Security audit log
)
```

**Zmienne środowiskowe** (`.env`):

- `DB_CONN_STR` (WYMAGANE): Connection string MS SQL (format SQLAlchemy).

**Przykład Connection String**:

```
mssql+pyodbc://user:password@SERVER\INSTANCE/database?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

### Connection Pooling

Konfiguracja puli połączeń (optymalizacja wydajności):

```python
create_engine(
    conn_str,
    pool_pre_ping=True,       # Weryfikuj połączenie przed użyciem (stale connections)
    pool_size=5,              # Liczba persystentnych połączeń
    max_overflow=10,          # Dodatkowe połączenia w szczycie
    pool_recycle=3600,        # Recykling połączeń co 1h (zapobiega stale)
    pool_timeout=30           # Timeout oczekiwania na połączenie z puli (sekundy)
)
```

### Caching Mechanizm

**Cache TTL**: 300 sekund (5 minut) - konfigurowalne przez `_cache_ttl`.

**Cache Key Pattern**: `{query_name}_{param1}_{param2}...`

**Przykład**:

```python
# Cache key: "historical_data_2024-01-01_2024-12-31"
df = db.get_historical_data(date_from="2024-01-01", date_to="2024-12-31")
```

**Czyszczenie cache**:

```python
db.clear_cache()                    # Wszystkie
db.clear_cache("historical_data")  # Konkretny klucz
```

### Kluczowe Metody

#### 1. `get_historical_data(use_cache=True, date_from=None, date_to=None)`

**Cel**: Pobiera dane historyczne zużycia surowców w agregacji tygodniowej.

**Wyjście**: DataFrame z kolumnami `['Week', 'Year', 'TowarId', 'Quantity']`.

**Query SQL** (uproszczony):

```sql
SELECT
    DATEPART(ISO_WEEK, n.CZN_DataRealizacji) as Week,
    YEAR(n.CZN_DataRealizacji) as Year,
    e.CZE_TwrId as TowarId,
    SUM(e.CZE_Ilosc) as Quantity
FROM dbo.CtiZlecenieElem e WITH (NOLOCK)
JOIN dbo.CtiZlecenieNag n WITH (NOLOCK) ON e.CZE_CZNId = n.CZN_ID
JOIN CDN.Towary t WITH (NOLOCK) ON e.CZE_TwrId = t.Twr_TwrId
WHERE n.CZN_DataRealizacji IS NOT NULL
  AND e.CZE_Typ IN (1, 2)      -- Tylko surowce
  AND t.Twr_Typ != 2            -- Wykluczenie usług
  [AND n.CZN_DataRealizacji >= :date_from]  -- Opcjonalny filtr
  [AND n.CZN_DataRealizacji <= :date_to]
GROUP BY YEAR(n.CZN_DataRealizacji), DATEPART(ISO_WEEK, n.CZN_DataRealizacji), e.CZE_TwrId
ORDER BY Year, Week
```

**Parametry**:

- `date_from`, `date_to`: Filtrowanie zakresu dat (parametryzowane - **bezpieczne przed SQL Injection**).

**Zależności tabel**: `CtiZlecenieElem` → `CtiZlecenieNag` → `Towary`.

#### 2. `get_current_stock(use_cache=True)`

**Cel**: Pobiera aktualne stany magazynowe surowców.

**Wyjście**: DataFrame `['TowarId', 'Code', 'Name', 'StockLevel', 'UsageCount']`.

**Logika**: Zwraca tylko surowce, które były użyte w produkcji (`UsageCount > 0`).

#### 3. `get_product_usage_stats(raw_material_id: int)`

**Cel**: Analizuje w jakich wyrobach gotowych był użyty dany surowiec.

**Wyjście**: DataFrame `['FinalProductId', 'FinalProductName', 'FinalProductCode', 'OrderCount', 'TotalUsage']`.

**Limit**: TOP 20 wyrobów (posortowane wg TotalUsage DESC).

**Użycie**: Panel Zakupowca - wykres "Gdzie używany surowiec".

#### 4. `get_product_bom(final_product_id: int)`

**Cel**: Pobiera recepturę (BOM) dla wyrobu gotowego.

**Wyjście**: DataFrame `['IngredientCode', 'IngredientName', 'QuantityPerUnit', 'Unit', 'Type']`.

**Logika**: Wybiera najnowszą technologię (max CTN_ID).

#### 5. `get_bom_with_stock(final_product_id: int, technology_id: int = None)`

**Cel**: BOM + aktualny stan magazynowy składników (dla AI - planowanie zakupów).

**Wyjście**: DataFrame `['IngredientCode', 'IngredientName', 'QuantityPerUnit', 'Unit', 'CurrentStock']`.

**Użycie**: AI Assistant - "Analiza Wyrobu Gotowego (BOM)".

### Diagnostyka Wydajności

**Klasa**: `QueryDiagnostics`

**Funkcje**:

- Logowanie czasu wykonania każdego zapytania.
- Ostrzeżenie o wolnych zapytaniach (> 1.0s).

**Statystyki**:

```python
stats = db.get_diagnostics_stats()
# Output: {'total_queries': 15, 'avg_duration': 0.32, 'max_duration': 1.2, 'slow_queries': 1}
```

---

## Silniki AI

Aplikacja wspiera **3 silniki AI**:

1. **Google Gemini** (Cloud)
2. **Ollama** (Local Server)
3. **Local LLM** (Embedded - llama-cpp-python)

### 1. Google Gemini Client

**Plik**: `src/ai_engine/gemini_client.py`

**Model**: `gemini-2.0-flash` (najnowszy, grudzień 2024).

**Parametry wejściowe**:

- `GEMINI_API_KEY` (zmienna środowiskowa) - klucz API Google.

**Metody**:

- `generate_explanation(prompt: str) -> str`: Generuje odpowiedź na prompt.

**Retry Logic**: 3 próby z exponential backoff (1s, 2s, 3s).

**Bezpieczeństwo**:

- Dane są **anonimizowane** przed wysyłką (moduł `anonymizer.py`).
- NIP, PESEL, email są maskowane (regex patterns).

### 2. OpenRouter Client (Cloud)

**Plik**: `src/ai_engine/openrouter_client.py`

**Model**: Konfigurowalny (domyślnie `meta-llama/llama-3.2-3b-instruct`).

**Parametry wejściowe**:

- `OPENROUTER_API_KEY` (zmienna środowiskowa).

**Metody**:

- `generate_explanation(prompt: str) -> str`: Generuje odpowiedź (interface kompatybilny z OpenAI).

**Zalety**:

- Dostęp do 100+ modeli (GPT-4o, Claude 3.5 Sonnet, Llama 3).
- Brak kosztów utrzymania infrastruktury.
- Modele darmowe dostępne w API.

**Bezpieczeństwo**:

- Anonimizacja danych przed wysłaniem.

### 3. Ollama Client

**Plik**: `src/ai_engine/ollama_client.py`

**Wymagania**: Uruchomiona usługa Ollama (`ollama serve`).

**Parametry**:

- `OLLAMA_HOST` (env, domyślnie: `http://localhost:11434`)
- `model_name` (domyślnie: `llama3.1`)

**Obsługiwane modele**:

- `llama3.2` (szybki, uniwersalny)
- `ministral-3:8b` (kompaktowy, szybki)

### 3. Local LLM Engine (Embedded)

**Plik**: `src/ai_engine/local_llm.py`

**Framework**: llama-cpp-python (GGUF format).

**Cel**: Pełna prywatność - LLM działa lokalnie bez połączenia z internetem.

**Rekomendowane Modele** (grudzień 2024):

| Model | Rozmiar | Kontekst | Opis |
|-------|---------|----------|------|
| **Qwen2.5-7B-Instruct** | 3.81 GB | 32k | **Zalecany** - najlepsza jakość/szybkość |
| Qwen2.5-3B-Instruct | 1.96 GB | 32k | Szybki, mniejsze wymagania |
| DeepSeek-R1-14B | 8.0 GB | 32k | Zaawansowane rozumowanie |
| Mistral-Small-24B | 14.0 GB | 32k | Najwyższa jakość |

**Lokalizacja modeli**: `models/*.gguf`

**Parametry inicjalizacji**:

```python
LocalLLMEngine(
    model_path: str = None,     # Ścieżka do pliku .gguf (z env: LOCAL_LLM_PATH)
    n_ctx: int = 2048,          # Context window size
    n_threads: int = None,      # CPU threads (auto-detect: CPU count - 2)
    verbose: bool = False       # Logging from llama.cpp
)
```

**Lazy Initialization**: Model jest ładowany przy pierwszym wywołaniu `generate()`.

---

## Moduły Machine Learning

### 1. Forecaster - Prognozowanie Popytu

**Plik**: `src/forecasting.py`

**Cel**: Predykcja zużycia surowców na 4 tygodnie w przód.

**Obsługiwane Modele**:

#### a) Baseline (SMA-4)

**Metoda**: `predict_baseline(df, weeks_ahead=4)`

**Algorytm**: Simple Moving Average z ostatnich 4 tygodni.

**Wzór**: `Pred(t+1) = AVG(Q(t-3), Q(t-2), Q(t-1), Q(t))`

**Użycie**: Punkt odniesienia (benchmark) dla ML modeli.

#### b) Random Forest

**Metoda**: `train_predict(df, weeks_ahead=4, model_type='rf')`

**Algorytm**: Ensemble decision trees (100 drzew).

**Feature Engineering**:

- `WeekOfYear`: Numer tygodnia (seasonality)
- `Month`: Miesiąc (seasonality)
- `Lag_1`, `Lag_2`, `Lag_3`: Wartości z t-1, t-2, t-3
- `Rolling_Mean_4`: Średnia krocząca z 4 tygodni

**Hiperparametry**:

```python
RandomForestRegressor(
    n_estimators=100,
    random_state=42
)
```

**Strategia Predykcji**: Recursive Multi-Step (predykcja t+1 staje się Lag_1 dla t+2).

**Minimalne dane**: 8 tygodni historii.

#### c) Gradient Boosting

**Metoda**: `train_predict(df, weeks_ahead=4, model_type='gb')`

**Algorytm**: Gradient Boosted Trees (sekwencyjne uczenie).

**Hiperparametry**:

```python
GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=3,
    random_state=42
)
```

**Przewaga**: Wyższa precyzja niż RF dla dużych zbiorów danych.

#### d) Exponential Smoothing (Holt-Winters)

**Metoda**: `train_predict(df, weeks_ahead=4, model_type='es')`

**Biblioteka**: statsmodels.tsa.holtwinters.ExponentialSmoothing

**Konfiguracja**:

- **Trend**: Additive (`trend='add'`)
- **Seasonality**: Additive (`seasonal='add'`, period=4 weeks) - jeśli >= 12 tygodni danych
- Fallback: Tylko trend jeśli < 12 tygodni

**Użycie**: Najlepszy dla danych z wyraźną sezonowością (np. popyt rośnie latem).

**Minimalne dane**: 5 tygodni.

### 2. Preprocessing

**Plik**: `src/preprocessing.py`

#### Funkcja: `prepare_time_series(df)`

**Wejście**: DataFrame z kolumnami `['Year', 'Week', 'TowarId', 'Quantity']`.

**Wyjście**: DataFrame z kolumną `'Date'` (Timestamp) utworzoną z ISO Week.

**Implementacja**:

```python
df['Date'] = df.apply(
    lambda row: pd.Timestamp.fromisocalendar(int(row['Year']), int(row['Week']), 1),
    axis=1
)
```

**Dzień**: Poniedziałek (day=1) reprezentuje tydzień.

#### Funkcja: `fill_missing_weeks(df)`

**Cel**: Wypełnia brakujące tygodnie zerami dla każdego produktu.

**Algorytm**:

1. Generuj pełny zakres dat (min → max) z częstotliwością `'W-MON'`.
2. Utwórz MultiIndex `(TowarId, Date)`.
3. Reindex DataFrame, wypełniając brakujące `Quantity=0`.

**Użycie**: Konieczne przed trenowaniem modeli ML (wymaga regularnych interwałów czasowych).

---

## Bezpieczeństwo

### 1. Audit Logging

**Plik**: `src/security/audit.py`

**Cel**: Logowanie zdarzeń związanych z bezpieczeństwem (compliance, monitoring).

**Format**: JSON (łatwe parsowanie).

**Typy Zdarzeń** (`AuditEventType`):

- `LOGIN_SUCCESS`, `LOGIN_FAILURE`
- `SESSION_START`, `SESSION_END`
- `DATA_ACCESS`, `DATA_EXPORT`
- `QUERY_EXECUTE`
- `CONFIG_CHANGE`, `SECRET_ACCESS`
- `AI_QUERY`, `AI_RESPONSE`
- `SECURITY_WARNING`, `SECURITY_ERROR`

**Klasa**: `SecurityAuditLog` (Singleton)

**Lokalizacja logów**: `logs/security_audit.log` (env: `AUDIT_LOG_PATH`).

**Rotacja**: 10 MB, 5 backup files (RotatingFileHandler).

### 2. Configuration Encryption

**Plik**: `src/security/encryption.py`

**Algorytm**: Fernet (AES-128-CBC + HMAC-SHA256).

**Key Derivation**: PBKDF2-SHA256 z 480,000 iteracji (OWASP 2023 recommendation).

**Parametry**:

- `ENCRYPTION_MASTER_KEY` (env, **WYMAGANE**) - master key
- `ENCRYPTION_SALT` (env, domyślnie: `AI_Supply_Assistant_v1_2025`) - salt dla KDF

⚠️ **UWAGA**: W produkcji master key powinien być w HSM lub Azure Key Vault.

### 3. Parametryzowane Zapytania SQL

**Standard**: Wszystkie zapytania używają parametrów SQLAlchemy:

```python
# BEZPIECZNE (parametryzowane):
query = "SELECT * FROM Towary WHERE Twr_TwrId = :product_id"
df = db.execute_query(query, params={"product_id": product_id})

# NIEBEZPIECZNE (SQL Injection risk):
# query = f"SELECT * FROM Towary WHERE Twr_TwrId = {product_id}"  # ❌ NIE UŻYWAĆ
```

**Przykłady SQL w dokumentacji**: Wszystkie zapytania INSERT/UPDATE powinny być w bloku transakcji:

```sql
BEGIN TRAN
INSERT INTO dbo.CtiZlecenieElem (CZE_TwrId, CZE_Ilosc) VALUES (123, 50.0)
-- Test query, verify results
ROLLBACK  -- Safety: Rollback by default in documentation
```

---

## Architektura GUI

### Wzorzec Projektowy

**Streamlit** + **MVVM** (Model-View-ViewModel).

### Komponenty Reusable

**Lokalizacja**: `src/gui/components/`

#### 1. Sidebar (`sidebar.py`)

**Funkcje**:

- `render_connection_settings(on_connect)`: Formularz połączenia ręcznego z SQL.
- `render_connection_status(is_connected)`: Wskaźnik statusu połączenia.
- `render_mode_selector()`: Wybór trybu aplikacji (Analiza/Predykcja/AI).
- `render_date_filters()`: Filtry zakresu dat.

**Bezpieczeństwo**:

- **NIE ma** domyślnych credentials (empty placeholders).
- Hasło w `type="password"` (masked input).

### Widoki (Views)

**Lokalizacja**: `src/gui/views/`

#### 1. Analysis View (`analysis.py`)

**Funkcja**: `render_analysis_view(...)`

**Funkcjonalności**:

- Wykres trendu zużycia (Plotly Line Chart).
- Panel Zakupowca:
  - Wykres "Gdzie używany surowiec" (TOP 20 wyrobów gotowych).
  - Interaktywna tabela BOM (Bill of Materials).
- Metryki (total quantity, avg per product).

**ViewModels**: `AnalysisViewModel` (MVVM separation).

#### 2. Prediction View (`prediction.py`)

**Funkcja**: `render_prediction_view(...)`

**Funkcjonalności**:

- Wybór modelu predykcyjnego (Baseline/RF/GB/ES).
- Prognoza na 4 tygodnie.
- Wykres: historyczny + prognoza (różne kolory).

**ViewModels**: `PredictionViewModel`.

#### 3. Assistant View (`assistant.py`)

**Funkcja**: `render_assistant_view(...)`

**Funkcjonalności**:

- Wybór silnika AI (Gemini/Ollama/Local LLM).
- **Model Comparison Mode**: Porównanie dwóch modeli lokalnych (benchmark).
- 2 tryby analizy:
  - **Analiza Surowca (Anomalie)**: Detekcja anomalii trendu + rekomendacje.
  - **Analiza Wyrobu Gotowego (BOM)**: Planowanie zakupów na podstawie BOM + stany magazynowe.

---

## ViewModels (MVVM)

**Lokalizacja**: `src/viewmodels/`

### Wzorzec MVVM

**Separacja odpowiedzialności**:

- **View**: Renderowanie UI (Streamlit components).
- **ViewModel**: Logika biznesowa, transformacja danych, state management.
- **Model**: Źródło danych (DatabaseConnector, Forecaster).

### 1. Base ViewModel

**Plik**: `src/viewmodels/base_viewmodel.py`

**Klasy**:

- `ViewModelState`: Base dataclass dla stanu ViewModel.
- `LoadingState`: Enum (IDLE, LOADING, SUCCESS, ERROR).
- `BaseViewModel`: Bazowa klasa abstrakcyjna.

### 2. Analysis ViewModel

**Plik**: `src/viewmodels/analysis_viewmodel.py`

**Klasy**:

- `AnalysisSummary`: Statystyki (total_quantity, top_products, trend_direction).
- `AnalysisState`: Stan (df_stock, df_historical, df_filtered, product_map, summary).
- `AnalysisViewModel`: Logika analizy danych.

**Metody**:

- `load_all_data(force_refresh=False)`: Ładuje stock + historical data.
- `apply_date_filter(start_date, end_date)`: Filtruje dane po dacie.
- `calculate_summary()`: Oblicza statystyki (total quantity, top products, trend).

---

## Usługi Asynchroniczne

### Async Data Loader

**Plik**: `src/services/async_loader.py`

**Cel**: Ładowanie danych w tle (ThreadPoolExecutor) bez blokowania GUI.

**Problem**: Długie zapytania SQL (> 5s) blokują UI w Streamlit.

**Rozwiązanie**: Asynchroniczne wykonanie query w osobnym wątku.

**Klasy**:

- `LoadingState`: Enum (IDLE, LOADING, COMPLETED, ERROR).
- `LoadResult`: Kontener wyniku (state, data, error, duration_ms).
- `AsyncDataLoader`: Główna klasa.

**Thread Pool**:

- Wspólny pula dla wszystkich instancji (Singleton pattern).
- Liczba workerów: 3.

**Metody**:

#### `load_async(task_id, loader_fn, force_reload=False, cache_ttl=300.0)`

**Parametry**:

- `task_id`: Unikalny ID zadania (np. `"historical_data_2024"`).
- `loader_fn`: Funkcja ładująca dane (callable, np. `lambda: db.get_historical_data()`).
- `cache_ttl`: Czas życia cache (sekundy).

**Zwraca**: `LoadResult`

---

## Deployment i Konfiguracja

### Zmienne Środowiskowe (.env)

**Wymagane**:

```bash
# Database Connection (REQUIRED)
DB_CONN_STR=mssql+pyodbc://user:pass@SERVER\INSTANCE/database?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

**Opcjonalne (AI)**:

```bash
# Google Gemini (Cloud AI)
GEMINI_API_KEY=AIzaSyC...

# Ollama (Local Server AI)
OLLAMA_HOST=http://localhost:11434

# Local LLM (Embedded AI)
LOCAL_LLM_PATH=models/qwen2.5-7b-instruct-q3_k_m.gguf
```

**Opcjonalne (Security)**:

```bash
# Encryption
ENCRYPTION_MASTER_KEY=your_master_key_here
ENCRYPTION_SALT=unique_installation_salt

# Audit Log
AUDIT_LOG_PATH=logs/security_audit.log
```

### Instalacja Zależności

**Główne biblioteki**:

- `streamlit>=1.30`
- `pandas>=1.5`
- `sqlalchemy>=2.0`
- `pyodbc>=4.0`
- `plotly>=5.0`
- `scikit-learn>=1.3`
- `statsmodels>=0.14`
- `google-generativeai>=0.3`
- `llama-cpp-python>=0.3.2`
- `cryptography>=41.0`
- `python-dotenv>=1.0`

**Instalacja**:

```bash
pip install -r requirements.txt
```

### Uruchomienie Aplikacji

**Development**:

```bash
streamlit run main.py
```

**Production**:

```bash
streamlit run main.py --server.port 8501 --server.address 0.0.0.0
```

---

## Procedury Testowania

### Skrypty Testowe

**Lokalizacja**: `scripts/`

**Przykłady**:

- `test_db.py`: Test połączenia z bazą.
- `test_ml_pipeline.py`: Test pipeline ML (preprocessing → forecasting).
- `test_qwen_7b.py`: Test modelu Qwen2.5-7B.
- `test_ollama.py`: Test integracji z Ollama.
- `test_security.py`: Test modułów bezpieczeństwa.
- `verify_app_logic.py`: Test logiki aplikacji.
- `compare_models.py`: Benchmark modeli LLM.

### Performance Testing

**Metryki**:

- Query execution time (target: < 1.0s).
- Forecast generation time (target: < 5.0s dla 1 produktu).
- LLM response time (Local LLM: 10-30s, Gemini: 2-5s).

### Security Testing

**Checklist**:

- ✅ Parametryzowane zapytania SQL (wszystkie metody `execute_query`).
- ✅ Brak hardcoded credentials w kodzie.
- ✅ `.env.example` nie zawiera prawdziwych secrets.
- ✅ `.gitignore` zawiera `.env`, `logs/`, `*.log`.
- ✅ Anonimizacja PII przed wysyłką do Gemini.

---

## Glossary (Słowniczek Terminów)

| Termin | Definicja |
|--------|-----------|
| **BOM** | Bill of Materials - receptura/skład wyrobu gotowego |
| **CTE** | CtiTechnolElem - elementy technologii (BOM) |
| **CTI** | Produkcja by CTI - moduł produkcji dla Comarch Optima |
| **CZE** | CtiZlecenieElem - elementy zlecenia produkcyjnego (surowce użyte) |
| **CZN** | CtiZlecenieNag - nagłówek zlecenia produkcyjnego |
| **GGUF** | GPT-Generated Unified Format - format modeli LLM dla llama.cpp |
| **MVVM** | Model-View-ViewModel - wzorzec architektoniczny |
| **NOLOCK** | SQL Hint - odczyt bez blokowania tabel (dirty reads possible) |
| **PII** | Personally Identifiable Information - dane osobowe |
| **TTL** | Time To Live - czas życia cache |

---

**KONIEC DOKUMENTACJI TECHNICZNEJ**

**Wersja**: 1.0
**Status**: ✅ Kompletna - Wszystkie moduły udokumentowane
**Ostatnia aktualizacja**: 2024-12-29
