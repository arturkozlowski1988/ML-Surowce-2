# 📖 Instrukcja Obsługi: AI Supply Assistant

> **Wersja**: 1.6.0
> **Data aktualizacji**: 2026-01-10
> **Status**: Oficjalna dokumentacja użytkownika

---

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Szybki Start](#szybki-start)
3. [Logowanie i Uprawnienia](#logowanie-i-uprawnienia)
4. [Główne Moduły](#główne-moduły)
   - [Analiza Danych (Panel Zakupowca)](#moduł-analiza-danych)
   - [Predykcja Popytu (ML)](#moduł-predykcja-ml)
   - [MRP Lite (Symulacja Produkcji)](#moduł-mrp-lite)
   - [Inteligentny Asystent (AI/LLM)](#moduł-ai-assistant)
5. [Panel Administracyjny](#panel-administracyjny)
6. [Rozwiązywanie Problemów](#rozwiązywanie-problemów)

---

## Wprowadzenie

**AI Supply Assistant** to zaawansowane narzędzie wspierające działy zakupów i produkcji. System integruje się z Twoim oprogramowaniem ERP (Comarch Optima / CTI), aby pomagać w podejmowaniu lepszych decyzji zakupowych.

**Co zyskujesz?**
- 📉 **Mniejsze ryzyko przestojów** dzięki predykcji braków i alertom.
- 💰 **Optymalizację stanów magazynowych** – algorytmy ML podpowiadają, ile dokładnie zamówić.
- ⏱️ **Oszczędność czasu** przy analizie BOM (AI automatycznie analizuje strukturę wyrobu).
- 🧠 **Wsparcie AI** – lokalne i chmurowe modele językowe pomagają w analizie danych.

---

## Szybki Start

### Uruchomienie aplikacji

Aplikacja jest dostępna przez przeglądarkę internetową. Skontaktuj się z administratorem IT, aby uzyskać adres (np. `http://serwer-produkcja:8501`).

### Pierwsze kroki

1. **Zaloguj się** przydzielonym loginem i hasłem.
2. W **Panelu Bocznym** (po lewej) wybierz bazę danych (jeśli masz dostęp do kilku).
3. Wybierz **Magazyn**, który Cię interesuje (lub zostaw puste, by widzieć wszystkie).
4. Przejdź do modułu **Analiza Danych**, aby zobaczyć ogólny stan zapasów.

---

## Logowanie i Uprawnienia

System obsługuje dwa główne poziomy dostępu (RBAC):

| Rola | Dostępne funkcje |
|------|------------------|
| **Administrator** | Pełny dostęp do wszystkich modułów. Zarządzanie użytkownikami, konfiguracja AI (modele, klucze API), strojenie parametrów ML, konfiguracja alertów, audyt logów. |
| **Zakupowiec** | Analiza Danych, Predykcja (ML), MRP Lite, AI Assistant. Dostęp do Panelu Zakupowca. Brak dostępu do ustawień systemowych. |

> 🔒 **Bezpieczeństwo**: Hasła są szyfrowane. Jeśli zapomnisz hasła, skontaktuj się z Administratorem w celu jego zresetowania.

---

## Główne Moduły

### Moduł: Analiza Danych

Podstawowe narzędzie do przeglądu historii i struktury produktów.

1. **Filtry**: Ustaw zakres dat w panelu bocznym.
2. **Wykresy**: Wizualizacja trendu zużycia dla wybranych surowców.
3. **Panel Zakupowca**: Po wybraniu **jednego** surowca zobaczysz szczegółową analizę:
   - **Gdzie używany?**: Wykres pokazujący wyroby gotowe, w których ten surowiec występuje.
   - **Analiza BOM**: Możliwość podglądu pełnej struktury materiałowej wyrobu, w którym używany jest surowiec.

---

### Moduł: Predykcja ML

Prognozowanie zapotrzebowania z wykorzystaniem algorytmów uczenia maszynowego.

**Dostępne modele:**
- **Random Forest (Zbalansowany)**: Dobry balans między dokładnością a szybkością.
- **Gradient Boosting (Wysoka Precyzja)**: Często najdokładniejszy, uczy się na błędach poprzedników.
- **Exponential Smoothing (Trend/Sezonowość)**: Klasyczna metoda, idealna przy silnej, regularnej sezonowości.
- **LSTM (Deep Learning)**: Zaawansowana sieć neuronowa, rozpoznaje złożone, nieliniowe wzorce (wymaga więcej danych i dłuższego czasu treningu).

**Interpretacja Biznesowa:**
System nie tylko wyświetla wykres, ale generuje **wnioski biznesowe**:
- Sumaryczne przewidywane zapotrzebowanie.
- Trend (wzrost/spadek).
- Rekomendacja bezpiecznego poziomu zapasów (np. 110% prognozy).

---

### Moduł: MRP Lite

Symulator produkcji i centrum zarządzania brakami.

#### 1. Panel Produkcyjny CTI (Dashboard)
Widok "na żywo" statystyk produkcyjnych:
- Liczba aktywnych zleceń.
- Liczba dokumentów braków.
- Obciążenie technologii i zasobów.

#### 2. Symulator "Co-Jeśli"
Pozwala sprawdzić wykonalność produkcji przed wystawieniem zlecenia.
1. Wybierz wyrób gotowy.
2. Podaj planowaną ilość.
3. Kliknij **Uruchom Symulację**.

**Wyniki symulacji:**
- ✅ **Status produkcji**: Czy można wyprodukować zadaną ilość?
- ⚠️ **Braki**: Lista brakujących surowców z czasem dostawy.
- 🔄 **Inteligentne Zamienniki (Smart Substitutes)**: Jeśli brakuje składnika, a w systemie zdefiniowano zamiennik, system go zasugeruje.
- **Bottleneck**: Wskazanie elementu najbardziej ograniczającego produkcję.

#### 3. Dashboard Krytycznych Braków (Alerty)
Automatyczna lista surowców, których stan jest krytyczny w stosunku do średniego zużycia.
- 🔴 **Krytyczne**: Zapas na wyczerpaniu (domyślnie < 7 dni).
- 🟡 **Niskie**: Zapas poniżej bezpiecznego poziomu.

---

### Moduł: AI Assistant

Inteligentny asystent wspierający analizę danych (GenAI).

**Tryby pracy:**
1. **Analiza Surowca (Anomalie)**: Wybierz surowiec, aby AI przeanalizowała historię zużycia, wykryła anomalie i oceniła bezpieczeństwo zapasu.
2. **Analiza Wyrobu Gotowego (BOM)**: Wybierz wyrób i ilość do produkcji. AI przeanalizuje dostępność komponentów (również na innych magazynach) i zasugeruje działania dla działu zakupów.

**Funkcje dodatkowe:**
- **Tryb Porównania (Benchmark)**: Pozwala uruchomić analizę na dwóch różnych modelach AI jednocześnie (np. Local LLM vs Google Gemini), aby porównać jakość odpowiedzi.
- **Wsparcie wielu silników**:
    - **Local LLM**: Modele działające w pełni lokalnie na serwerze (np. Mistral, Llama). Pełna prywatność.
    - **Ollama**: Integracja z lokalnym serwerem Ollama.
    - **Chmura (Google Gemini, OpenRouter)**: Dostęp do najpotężniejszych modeli (wymaga klucza API).

> ⚠️ **Uwaga**: Asystent działa w trybie zadaniowym (analiza konkretnych danych). Nie służy do ogólnych rozmów (czat ogólny).

---

## Panel Administracyjny

(Moduł dostępny tylko dla użytkowników z rolą Administrator)

Zarządzanie całym systemem podzielone jest na zakładki:

1. **Dashboard**: Statystyki użycia systemu, liczba użytkowników, historia zapytań AI.
2. **Użytkownicy**:
   - Tworzenie i usuwanie kont.
   - Resetowanie haseł.
   - Przypisywanie ról (Admin/Zakupowiec).
3. **Ustawienia LLM**:
   - Wybór domyślnego silnika AI.
   - Konfiguracja kluczy API (Gemini, OpenRouter).
   - Adres serwera Ollama.
4. **Pobieranie Modeli**:
   - Pobieranie modeli GGUF bezpośrednio z HuggingFace.
   - Zarządzanie lokalnymi plikami modeli (usuwanie).
5. **Konfiguracja ML**:
   - Zaawansowane strojenie hiperparametrów modeli (np. liczba drzew w Random Forest, epoki w LSTM).
6. **Uprawnienia Baz**:
   - Przypisywanie konkretnych baz danych do użytkowników.
   - Przypisywanie domyślnych silników AI per użytkownik.
7. **Alerty**:
   - Konfiguracja progów dla alertów (dni zapasu).
   - Włączanie powiadomień e-mail.
8. **Edycja Promptów**: Modyfikacja szablonów zapytań wysyłanych do AI.
9. **Audyt**: Przegląd szczegółowych logów aktywności użytkowników.
10. **Ustawienia Systemowe**: Konfiguracja pamięci podręcznej (Cache TTL) i horyzontu prognoz.

---

## Rozwiązywanie Problemów

| Problem | Rozwiązanie |
|---------|-------------|
| **Brak towaru na liście** | Sprawdź filtry dat oraz czy wybrano odpowiedni magazyn. Towar musi mieć historię ruchu w zadanym okresie. |
| **Symulacja trwa długo** | Przy bardzo złożonych wyrobach (wielopoziomowe BOM) analiza może potrwać do 10-15 sekund. |
| **Błąd API (AI)** | Sprawdź w *Panelu Admina -> Ustawienia LLM*, czy klucze API (Gemini/OpenRouter) są poprawne i mają dostępne środki. |
| **Brak modelu Lokalnego** | Jeśli Asystent zgłasza brak modelu, Administrator musi pobrać model w zakładce *Panel Admina -> Pobieranie Modeli*. |
| **Błąd LSTM** | Model LSTM wymaga zainstalowanej biblioteki TensorFlow. Skontaktuj się z administratorem, jeśli opcja jest nieaktywna. |
| **Problemy z logowaniem** | Skontaktuj się z Administratorem w celu resetu hasła. |

---
*Dokumentacja przygotowana dla systemu AI Supply Assistant.*
