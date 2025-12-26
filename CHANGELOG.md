# Changelog

Wszystkie znaczące zmiany w projekcie są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

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
