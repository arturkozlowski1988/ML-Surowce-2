# 📖 Instrukcja Obsługi: AI Supply Assistant

> **Wersja**: 1.8.0
> **Data aktualizacji**: 2026-01-24
> **Status**: Oficjalna dokumentacja użytkownika

---

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Logowanie i Konfiguracja](#logowanie-i-konfiguracja)
   - [Logowanie do systemu](#logowanie-do-systemu)
   - [Wybór Bazy Danych i Magazynów](#wybór-bazy-danych-i-magazynów)
3. [Moduł: Analiza Danych](#moduł-analiza-danych)
4. [Moduł: Predykcja Popytu (ML)](#moduł-predykcja-popytu-ml)
5. [Moduł: MRP Lite (Symulator)](#moduł-mrp-lite-symulator)
   - [Symulacja Produkcji](#symulacja-produkcji)
   - [Krytyczne Braki](#krytyczne-braki)
6. [Moduł: Asystent AI](#moduł-asystent-ai)
7. [Panel Administratora](#panel-administratora)
8. [Rozwiązywanie Problemów](#rozwiązywanie-problemów)

---

## Wprowadzenie

**AI Supply Assistant** to inteligentne narzędzie wspierające procesy planowania produkcji i zakupów. System integruje się z danymi ERP (Comarch Optima / CTI), oferując zaawansowaną analitykę, predykcję popytu oraz symulacje dostępności materiałowej w czasie rzeczywistym.

**Kluczowe możliwości:**
*   **Predykcja Popytu**: Wykorzystanie AI do przewidywania zapotrzebowania na 4 tygodnie w przód.
*   **Symulacja MRP**: Sprawdzanie wykonalności produkcji z uwzględnieniem zamienników (Smart Substitutes).
*   **Inteligentne Alerty**: Automatyczne wykrywanie zagrożeń ciągłości produkcji.
*   **Asystent GenAI**: Czat z AI pozwalający na analizę sytuacji rynkowej i materiałowej językiem naturalnym.

---

## Logowanie i Konfiguracja

### Logowanie do systemu
Po uruchomieniu aplikacji zobaczysz ekran logowania.
1. Wprowadź swoją **Nazwę użytkownika** i **Hasło**.
2. Kliknij przycisk **Zaloguj**.

System obsługuje dwa poziomy uprawnień:
*   **Zakupowiec**: Dostęp do analiz, predykcji, MRP i asystenta AI.
*   **Administrator**: Pełny dostęp, w tym zarządzanie użytkownikami, konfiguracja AI i audyt.

### Wybór Bazy Danych i Magazynów
Po zalogowaniu, w **Panelu Bocznym (Sidebar)** po lewej stronie znajdziesz opcje konfiguracyjne:

*   **Wybór Bazy Danych**: Jeśli masz dostęp do wielu podmiotów, wybierz odpowiednią bazę z listy.
*   **Wybór Magazynów**: Możesz filtrować dane dla konkretnych magazynów. Pozostawienie pola pustego oznacza analizę **wszystkich magazynów**.
*   **Zakres Dat**: Globalny filtr dat (np. "Ostatnie 6 miesięcy") wpływający na analizę historyczną.

> ℹ️ **Pierwsze Uruchomienie**: Jeśli system nie jest skonfigurowany, Administrator zobaczy **Kreator Połączenia**, który krok po kroku pomoże połączyć się z serwerem SQL.

---

## Moduł: Analiza Danych

Moduł ten służy do przeglądu historycznych trendów zużycia materiałów.

1. **Lista Towarów**: Po lewej stronie zobaczysz listę surowców posortowaną według całkowitego zużycia (możesz wyszukiwać po nazwie lub kodzie).
2. **Wykres Zużycia**: Główny wykres liniowy pokazuje historyczne zużycie tygodniowe wybranego surowca.
3. **Szczegóły**:
    *   **Statystyki**: Całkowita ilość zużyta, średnia tygodniowa.
    *   **Gdzie używany?**: Sekcja pokazująca TOP 20 wyrobów gotowych, do produkcji których używany jest dany surowiec.
    *   **Struktura (BOM)**: Podgląd składników (jeśli wybrano wyrób gotowy).

---

## Moduł: Predykcja Popytu (ML)

Narzędzie do prognozowania przyszłego zapotrzebowania na surowce.

**Kroki:**
1. Wybierz surowiec z listy.
2. Wybierz **Model Predykcyjny**:
    *   **Random Forest / Gradient Boosting**: Najlepsze do typowych danych produkcyjnych (uwzględniają trendy i sezonowość).
    *   **Exponential Smoothing (Holt-Winters)**: Idealny dla danych o bardzo silnej, regularnej sezonowości.
    *   **LSTM (Deep Learning)**: Zaawansowana sieć neuronowa (wymaga dużej ilości danych historycznych).
    *   **Baseline (Średnia)**: Prosta średnia z ostatnich 4 tygodni (punkt odniesienia).

**Wyniki:**
Wykres pokaże linię historyczną (niebieska) oraz prognozę na kolejne 4 tygodnie (czerwona przerywana).
*   **MAPE (Średni Błąd Procentowy)**: Im niższa wartość, tym model jest dokładniejszy.

---

## Moduł: MRP Lite (Symulator)

Serce operacyjne systemu, podzielone na dwie zakładki.

### 1. Symulacja Produkcji ("Co-Jeśli")
Pozwala sprawdzić, czy firma posiada materiały do wyprodukowania określonej partii towaru **zanim** zlecenie zostanie wystawione w ERP.

1. **Wybierz wyrób**: Wskaż produkt finalny.
2. **Wpisz ilość**: Podaj planowaną wielkość produkcji.
3. Kliknij **Uruchom Symulację** lub **Pełna Analiza AI**.

**Co zobaczysz?**
*   ✅ **Możliwa Produkcja**: Zielony komunikat, jeśli stany są wystarczające.
*   ⚠️ **Braki**: Czerwony/Żółty komunikat z informacją, ile maksymalnie można wyprodukować.
*   **Bottleneck (Wąskie Gardło)**: Wskazanie surowca, który najbardziej ogranicza produkcję.
*   **Smart Substitutes**: System podpowie **zamienniki** zdefiniowane w bazie, jeśli podstawowego składnika brakuje.
*   **Tabela BOM**: Szczegółowa lista materiałów z kolorami statusów (OK, BRAK, KRYTYCZNY).

### 2. Krytyczne Braki (Dashboard)
Automatyczny monitoring stanów magazynowych.
*   System analizuje średnie zużycie tygodniowe każdego surowca.
*   Jeśli zapas spadnie poniżej ustalonego progu (np. na 7 dni produkcji), surowiec trafi na listę **Krytycznych Braków**.
*   **Wyjaśnienie AI**: Możesz poprosić AI o analizę przyczyn braków dla wyświetlonej listy.

---

## Moduł: Asystent AI

Czat z inteligentnym asystentem, który ma dostęp do danych Twojej firmy (w trybie tylko do odczytu).

**Tryby pracy:**
1. **Analiza Surowca (Anomalie)**: Pytaj o konkretny surowiec. AI przeanalizuje jego historię, wykryje anomalie w zużyciu i oceni bezpieczeństwo zapasu.
2. **Analiza Wyrobu Gotowego (BOM)**: Pytaj o plan produkcji. AI przeanalizuje dostępność wszystkich składników i zasugeruje strategię zakupową.
3. **Porównanie (Benchmark)**: (Dla zaawansowanych) Uruchom zapytanie na dwóch modelach AI jednocześnie, aby porównać jakość odpowiedzi.

> 🔒 **Prywatność**: Jeśli Administrator skonfigurował **Local LLM**, Twoje dane nie opuszczają sieci firmowej. W przypadku modeli chmurowych (np. Gemini, OpenRouter), dane są anonimizowane przed wysłaniem.

---

## Panel Administratora

Dostępny tylko dla użytkowników z rolą `admin`.

### Główne Zakładki:
*   **Dashboard**: Statystyki użycia systemu, liczba zapytań AI, aktywność użytkowników.
*   **Użytkownicy**: Dodawanie nowych kont, resetowanie haseł, usuwanie użytkowników.
*   **Ustawienia LLM**:
    *   Wybór silnika (Google Gemini, OpenRouter, Ollama, Local LLM).
    *   Wprowadzanie kluczy API.
    *   Zarządzanie modelami (np. wybór `gpt-4` lub `llama-3` przez OpenRouter).
*   **Pobieranie Modeli**: Narzędzie do pobierania lokalnych modeli `.gguf` bezpośrednio z HuggingFace.
*   **Konfiguracja ML**: Dostrajanie parametrów modeli predykcyjnych (np. `learning_rate`, `epochs`).
*   **Uprawnienia Baz**: Przypisywanie użytkowników do konkretnych baz danych (jeśli firma obsługuje wiele podmiotów).
*   **Alerty**: Konfiguracja progów (ile dni zapasu to stan krytyczny) oraz powiadomień e-mail.
*   **Audyt**: Przegląd logów bezpieczeństwa (kto, kiedy i co robił w systemie).

---

## Rozwiązywanie Problemów

| Problem | Możliwa przyczyna | Rozwiązanie |
|---------|-------------------|-------------|
| **Błąd połączenia z bazą** | Problem z VPN lub serwerem SQL. | Sprawdź połączenie sieciowe. Skontaktuj się z IT. |
| **Brak surowca na liście** | Surowiec nie miał ruchów w zadanym okresie. | Zmień zakres dat w panelu bocznym na szerszy. |
| **Symulacja trwa długo** | Skomplikowany BOM (wielopoziomowy). | Odczekaj do 15-20 sekund. To normalne przy złożonych wyrobach. |
| **Asystent AI nie odpowiada** | Brak modelu lub klucza API. | (Admin) Sprawdź konfigurację w zakładce Ustawienia LLM. |
| **Błąd "Missing Weeks"** | Dane historyczne są dziurawe. | System automatycznie uzupełnia luki zerami, ale dla modeli ML wymagana jest minimalna ilość danych (min. 8 tygodni). |

---
*Dokumentacja przygotowana dla systemu AI Supply Assistant.*
