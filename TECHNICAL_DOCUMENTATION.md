# Dokumentacja Techniczna: AI Supply Assistant

> **Wersja**: 1.6.0
> **Data aktualizacji**: 2026-01-24
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
9. [Usługi Systemowe](#usługi-systemowe)
10. [Deployment i Konfiguracja](#deployment-i-konfiguracja)

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
│   │       ├── assistant.py     # AI assistant view
│   │       ├── connection_wizard.py # First-run setup
│   │       └── mrp_view.py      # MRP simulation view
│   ├── services/
│       ├── alerts.py            # Intelligent shortage detection
│       ├── async_loader.py      # Async data loading
│       ├── model_downloader.py  # GGUF models downloader
│       └── mrp_simulator.py     # MRP simulation engine
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
- `get_db_connection()`: Cached factory dla DatabaseConnector.
- Obsługa **Connection Wizard** przy pierwszym uruchomieniu.

**Routing logika**:

```python
if app_mode == "Analiza Danych":
    render_analysis_view(...)
elif app_mode == "MRP Lite":
    render_mrp_view(...)
elif app_mode == "Panel Admina":
    render_admin_view(...)
```

---

## Baza Danych - Schemat SQL

### Źródło Danych: Comarch Optima / CTI Module

System integruje się z modułem produkcji **Produkcja by CTI** dla Comarch Optima.

### Kluczowe Tabele

#### 1. `dbo.CtiZlecenieNag` (Production Order Header)
Nagłówek zlecenia produkcyjnego. Kluczowe pola: `CZN_ID`, `CZN_TwrId`, `CZN_DataRealizacji`.

#### 2. `dbo.CtiZlecenieElem` (Production Order Elements)
Składniki wykorzystane w produkcji. Filtrowanie surowców: `CZE_Typ IN (1, 2)`.

#### 3. `dbo.CtiTechnolNag` & `dbo.CtiTechnolElem` (BOM)
Definicja technologii produkcji (receptury).

#### 4. `CDN.Towary` & `CDN.TwrZasoby`
Katalog produktów i aktualne stany magazynowe.

---

## Moduł DatabaseConnector

**Plik**: `src/db_connector.py`

### Cel Biznesowy
Centralna warstwa dostępu do danych SQL. Zapewnia pooling połączeń, caching zapytań i diagnostykę.

### Kluczowe Metody
1. `get_historical_data()`: Pobiera dane zużycia w agregacji tygodniowej.
2. `get_current_stock()`: Pobiera stany magazynowe.
3. `get_bom_with_stock()`: Pobiera strukturę materiałową ze stanami (dla MRP).
4. `get_smart_substitutes()`: Wyszukuje zamienniki dla brakujących surowców.

---

## Silniki AI

Aplikacja wspiera **4 źródła AI**:

1. **Google Gemini** (Cloud): Model `gemini-2.0-flash`. Tani, szybki, wymaga klucza API.
2. **OpenRouter** (Cloud): Agregator modeli (GPT-4, Claude, Llama 3). Dostęp do 100+ modeli.
3. **Ollama** (Local Server): Zewnętrzny serwer Ollama (np. `http://localhost:11434`).
4. **Local LLM** (Embedded): Wbudowany silnik `llama-cpp-python` uruchamiający pliki `.gguf`.

**Bezpieczeństwo**:
Dla silników chmurowych (Gemini, OpenRouter) stosowana jest **anonimizacja danych** (moduł `anonymizer.py`) przed wysłaniem zapytania.

---

## Moduły Machine Learning

### 1. Forecaster - Prognozowanie Popytu
**Plik**: `src/forecasting.py`

**Obsługiwane Modele**:
*   **Baseline (SMA-4)**: Średnia krocząca.
*   **Random Forest**: Drzewa decyzyjne.
*   **Gradient Boosting**: Sekwencyjne uczenie.
*   **LSTM**: Sieć neuronowa (Deep Learning).
*   **Holt-Winters**: Exponential Smoothing (dla sezonowości).

### 2. Preprocessing
**Plik**: `src/preprocessing.py`
Przygotowuje szeregi czasowe: uzupełnia brakujące tygodnie zerami, tworzy features (lags, rolling means).

---

## Bezpieczeństwo

### 1. Audit Logging
**Plik**: `src/security/audit.py`
Rejestruje logowania, zmiany konfiguracji i zapytania AI. Logi są rotowane.

### 2. RBAC (Role-Based Access Control)
Role: `ADMIN`, `PURCHASER`.
Admin ma dostęp do `admin_view.py`, użytkownik tylko do modułów operacyjnych.

---

## Usługi Systemowe

### 1. MRP Simulator (`src/services/mrp_simulator.py`)
Silnik rekurencyjny analizujący drzewo BOM. Sprawdza dostępność składników na każdym poziomie, uwzględniając czasy dostaw.

### 2. Smart Alerts (`src/services/alerts.py`)
Monitoruje stany magazynowe w tle. Wykrywa towary, których zapas (Coverage Days) spadł poniżej progu krytycznego.

### 3. Model Downloader (`src/services/model_downloader.py`)
Umożliwia pobieranie modeli GGUF bezpośrednio z HuggingFace do katalogu `models/`.

---

## Deployment i Konfiguracja

**Zmienne Środowiskowe (.env)**:
```bash
DB_CONN_STR=mssql+pyodbc://...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
ENCRYPTION_MASTER_KEY=...
```

**Uruchomienie**:
```bash
streamlit run main.py
```

**Wymagania**:
Python 3.9+, SQL Server ODBC Driver 17.

---
**Status**: ✅ Zaktualizowano 2026-01-24
