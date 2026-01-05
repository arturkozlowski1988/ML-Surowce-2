# Changelog

## [1.4.1] - 2026-01-05

### Added

- **🎓 Prezentacja Akademicka**:
  - Całkowita restrukturyzacja `notebooks/prezentacja_akademicka.ipynb`
  - Struktura zgodna z programem studiów Merito "Analiza Danych - Data Science z elementami AI"
  - Fokus na realny problem biznesowy (zarządzanie zakupami surowców) i rozwiązanie
  - Praktyczne demonstracje: EDA, Machine Learning (RF, GB), AI Assistant (LLM)
  - Powiązania z technologiami z programu studiów

### Changed

- `readme.md` - dodana sekcja "Kontekst Akademicki" z informacjami o studiach podyplomowych
- `readme.md` - zaktualizowane informacje o autorze
- `TECHNICAL_DOCUMENTATION.md` - zaktualizowana wersja do 1.4.0, data do 2026-01-05

### Documentation

- Zaktualizowano linki do notebooków w dokumentacji
- Dodano informacje o Uniwersytecie WSB Merito Chorzów

---

## [1.4.0] - 2026-01-01

### Added

- **🔐 System Użytkowników i Uprawnień**:
  - Ekran logowania z uwierzytelnianiem bcrypt
  - Role: Administrator (pełny dostęp) i Zakupowiec (ograniczony)
  - Panel Admina: zarządzanie użytkownikami (dodawanie, usuwanie, zmiana haseł)
  - Zakupowiec nie może zmieniać bazy danych ani konfiguracji
  - Hasła hashowane bcrypt (bezpieczne przechowywanie w `config/users.json`)
  
- **🔌 Kreator Połączenia z Bazą Danych**:
  - Automatyczne wykrywanie lokalnych instancji SQL Server z rejestru Windows
  - 4-krokowy kreator: Serwer → Logowanie → Baza → Potwierdzenie
  - Obsługa SQL Auth i Windows Auth
  - Automatyczny zapis konfiguracji do `.env`
  - Przycisk "Uruchom Kreator Połączenia" w sidebar

- **🏭 Ulepszone Prompty AI**:
  - Analiza Surowca uwzględnia teraz stany magazynowe i wybrane magazyny
  - Obliczanie "Coverage" (na ile tygodni wystarczy zapasu)
  - Kontekst magazynów w promptach BOM

### Changed

- `main.py` v1.4.0 - dodano warstwę uwierzytelniania
- `sidebar.py` - wyświetlanie użytkownika, przycisk wyloguj, ukrywanie opcji wg roli
- Zaktualizowano dokumentację

### Security

- Hasła użytkowników hashowane algorytmem bcrypt
- Zabezpieczenie przed usunięciem ostatniego administratora
- Role-based access control (RBAC)

---

## [1.2.0] - 2025-12-29

### Added

- **Multi-database support** - Switch between cdn_test and cdn_mietex databases
- **Warehouse filtering** - Filter analysis by specific warehouses (magazyny)
- **Warehouse multiselect** in sidebar with stock summary
- **Database selector** in sidebar for easy switching
- **Info bar** showing active database and selected warehouse count
- `get_warehouses()` method in DatabaseConnector
- `warehouse_ids` parameter in stock and BOM queries

### Changed

- Updated `get_current_stock()` to support warehouse filtering
- Updated `get_bom_with_stock()` to support warehouse filtering
- Modified sidebar to include database and warehouse configuration
- Version bumped to 1.2.0

---

Wszystkie znaczące zmiany w projekcie są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

## [1.3.0] - 2024-12-28

### Dodano

- **🤖 Aktualizacja Modelu LLM - Qwen2.5-7B-Instruct**:
  - Ustawiono model 7B jako domyślny (zamiast 3B)
  - Wyższa jakość odpowiedzi i lepsze rozumowanie
  - Model GGUF (~3.55 GB) z kwantyzacją Q3_K_M
  - Zachowano backup model 3B do szybkich analiz
  
- **📊 Porównanie Modeli**:
  - Przeprowadzono testy porównawcze modeli (Qwen2.5 3B vs 7B)
  - Dokumentacja wyników w `models/MODEL_COMPARISON.md`
  - Skrypt `scripts/compare_models.py` do samodzielnych testów

### Zmieniono

- **⚙️ Konfiguracja `.env`**:
  - `LOCAL_LLM_PATH` teraz wskazuje na model 7B
  - Dodano komentarze z dostępnymi modelami

### Usunięto

- **🧹 Czyszczenie Projektu**:
  - Usunięto wszystkie foldery `__pycache__/` (8 folderów)
  - Usunięto `test_output.txt` (nieaktualny log błędów)
  - Usunięto pusty plik `OPTIMIZATION_ROADMAP.md`
  - Usunięto `models/comparison_results.txt` (przeniesiono do dokumentacji)
  - Wyczyszczono katalog `logs/` z plików `.log`

### Dokumentacja

- **📝 Aktualizacja Dokumentacji**:
  - `models/DOWNLOAD_STATUS.md` - status dostępnych modeli
  - `models/MODEL_COMPARISON.md` - pełne porównanie modeli

---

## [1.2.0] - 2024-12-27

### Dodano

- **🤖 Lokalny Model LLM - Qwen2.5-3B-Instruct**:
  - Najnowszy model (grudzień 2024) zoptymalizowany pod analizy biznesowe
  - Model GGUF (~1.96 GB) z kwantyzacją Q4_K_M
  - 32k kontekst - wsparcie dla długich dokumentów i analiz
  - Pełna prywatność - wszystkie dane przetwarzane lokalnie
  - Brak kosztów API - działa w pełni offline
  - Integracja z GUI - opcja "🚀 Local LLM (Embedded)" w AI Assistant
- **📝 Notebook testowy**: `notebooks/test_qwen25_model.ipynb`
- **📚 Dokumentacja**: `MODEL_SETUP_SUMMARY.md` - pełny przewodnik konfiguracji
- **✅ Aktualizacje dokumentacji**:
  - `readme.md` - sekcja o lokalnym modelu LLM
  - `.env.example` - instrukcje konfiguracji Qwen2.5
  - `local_llm.py` - dodano Qwen2.5 do listy rekomendowanych modeli

### Szczegóły techniczne

- **Model**: Qwen2.5-3B-Instruct-Q4_K_M (Alibaba Cloud/Qwen Team)
- **Framework**: llama-cpp-python 0.3.2 (wersja precompiled)
- **Lokalizacja**: `models/qwen2.5-3b-instruct-q4_k_m.gguf`
- **Konfiguracja**: `LOCAL_LLM_PATH=models/qwen2.5-3b-instruct-q4_k_m.gguf` w `.env`
- **Kontekst**: 32,768 tokenów (domyślnie używane 2048 dla wydajności)
- **Wątki CPU**: Auto-detect (CPU count - 2)

### Dlaczego Qwen2.5-3B?

✅ Najnowszy dostępny model (Q4 2024)  
✅ Doskonały do analiz biznesowych i supply chain  
✅ Duży kontekst (32k) vs Phi-3 (4k)  
✅ Optymalny rozmiar (1.96 GB)  
✅ 100% RODO-compliant - dane lokalne  

## [1.0.0] - 2025-12-26

### Dodano

- **Moduł Predykcji**: Obsługa 3 modeli (Random Forest, Gradient Boosting, Exponential Smoothing).
- **Panel Zakupowca**: Wizualizacja "Gdzie używany jest surowiec" + interaktywny BOM.
- **AI Assistant (GenAI)**:
  - Tryb "Analiza Surowca (Anomalie)" z wykrywaniem trendów.
  - Tryb "Analiza Wyrobu Gotowego (BOM)" z rekomendacjami zakupowymi.
  - Obsługa Ollama (lokalny LLM) i Google Gemini (Cloud).
- **Bezpieczeństwo**:
  - Moduł anonimizacji danych (NIP, PESEL, email) przed wysyłką do chmury.
  - Parametryzowane zapytania SQL (ochrona przed SQL Injection).
- **Dokumentacja**: `USER_GUIDE.md`, `README.md`, Jupyter Notebook demo.

### Poprawiono

- Poprawiono obsługę błędów w kliencie Gemini (retry logic).
- Zoptymalizowano zapytania SQL (cache, WITH NOLOCK).
- Filtrowanie usług z listy surowców (wykluczenie Twr_Typ = 2).

### Bezpieczeństwo

- Usunięto podatność SQL Injection w `get_bom_with_stock()`.
- Dodano `.env.example` jako szablon bez prawdziwych haseł.
- Rozszerzono `.gitignore` o pliki logów i konfiguracji.
