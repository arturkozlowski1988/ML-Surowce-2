# Changelog

Wszystkie znaczące zmiany w projekcie są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

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
