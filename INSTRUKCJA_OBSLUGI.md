# 📖 Instrukcja Obsługi: AI Supply Assistant

> **Wersja**: 1.7.0
> **Data aktualizacji**: 2026-01-11
> **Status**: Oficjalna dokumentacja użytkownika

---

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Szybki Start](#szybki-start)
3. [Logowanie i Uprawnienia](#logowanie-i-uprawnienia)
4. [Główne Moduły](#główne-moduły)
   - [Analiza Danych (Historie Zużycia)](#moduł-analiza-danych)
   - [Predykcja Popytu (ML)](#moduł-predykcja-ml)
   - [MRP Lite (Symulacja Produkcji)](#moduł-mrp-lite)
   - [Inteligentny Asystent (AI/LLM)](#moduł-ai-assistant)
5. [Panel Administracyjny](#panel-administracyjny)
6. [Rozwiązywanie Problemów](#rozwiązywanie-problemów)

---

## Wprowadzenie

**AI Supply Assistant** to zaawansowane narzędzie wspierające działy zakupów i produkcji. System integruje się z Twoim oprogramowaniem ERP (Comarch Optima / CTI), aby pomagać w podejmowaniu lepszych decyzji zakupowych.

**Co zyskujesz?**
- 📉 **Mniejsze ryzyko przestojów** dzięki predykcji braków (z wyprzedzeniem do 4 tygodni).
- 💰 **Optymalizację stanów magazynowych** – algorytmy ML podpowiadają, ile dokładnie zamówić.
- ⏱️ **Oszczędność czasu** przy analizie BOM (AI automatycznie analizuje strukturę wyrobu).

---

## Szybki Start

### Uruchomienie aplikacji

Aplikacja jest dostępna przez przeglądarkę internetową. Skontaktuj się z administratorem IT, aby uzyskać adres (np. `http://serwer-produkcja:8501`).

### Pierwsze kroki

1. **Zaloguj się** swoimi danymi domenowymi lub utworzonym kontem.
2. W **Panelu Bocznym** (po lewej) wybierz bazę danych (jeśli masz dostęp do kilku).
3. Wybierz **Magazyn**, który Cię interesuje (lub zostaw puste, by widzieć wszystkie).
4. Przejdź do modułu **Analiza Danych**, aby zobaczyć ogólny stan zapasów.

---

## Logowanie i Uprawnienia

System obsługuje dwa główne poziomy dostępu:

| Rola | Dostępne funkcje |
|------|------------------|
| **Administrator** | Pełny dostęp do wszystkich modułów, zarządzanie użytkownikami, konfiguracja połączeń DB, pobieranie modeli AI, audyt logów. |
| **Zakupowiec** | Analiza Danych, Predykcja (ML), MRP Lite, AI Assistant. Brak dostępu do ustawień systemowych i zarządzania kontami. |

> 🔒 **Bezpieczeństwo**: Hasła są szyfrowane. Jeśli zapomnisz hasła, skontaktuj się z Administratorem w celu jego zresetowania.

---

## Główne Moduły

### Moduł: Analiza Danych

Podstawowe narzędzie do przeglądu historii.

1. **Filtry**: Ustaw zakres dat w panelu bocznym.
2. **Tabela zbiorcza**: Zobaczysz listę towarów posortowaną wg największego zużycia.
3. **Szczegóły**: Kliknij na konkretny towar, aby zobaczyć:
   - Wykres zużycia w czasie.
   - **Gdzie używany?**: Listę wyrobów gotowych, w których ten surowiec występuje.
   - **BOM**: Strukturę materiałową.

---

### Moduł: Predykcja ML

Prognozowanie zapotrzebowania z wykorzystaniem algorytmów uczenia maszynowego.

**Dostępne modele:**
- **Random Forest / Gradient Boosting**: Najlepsze do ogólnych prognoz, uwzględniają trendy i proste sezonowości.
- **LSTM (Deep Learning)**: Zaawansowana sieć neuronowa, skuteczna przy złożonych, nieliniowych wzorcach (wymaga więcej danych).
- **Exponential Smoothing**: Klasyczna metoda statystyczna, idealna przy silnej, regularnej sezonowości.

**Jak interpretować wynik?**
System wyświetla prognozę na **4 tygodnie** w przód. Kluczowym wskaźnikiem jest **MAPE** (Średni Błąd Procentowy) – im niższa wartość, tym prognoza jest bardziej wiarygodna.

---

### Moduł: MRP Lite

Symulator produkcji i centrum zarządzania brakami.

#### 1. Panel Produkcyjny CTI (Dashboard)
Widok "na żywo" z hali produkcyjnej (dane z systemu CTI):
- **Aktywne Zlecenia**: Ilość otwartych zleceń produkcyjnych.
- **Braki**: Liczba dokumentów sygnalizujących braki materiałowe.
- **Zasoby**: Obciążenie gniazd produkcyjnych.

#### 2. Symulator "Co-Jeśli"
Pozwala sprawdzić wykonalność produkcji przed wystawieniem zlecenia.
1. Wybierz wyrób gotowy.
2. Podaj planowaną ilość.
3. Kliknij **Uruchom Symulację**.
4. (Opcjonalnie) Kliknij **Pełna Analiza AI**, aby otrzymać słowny opis sytuacji i rekomendacje.

**System sprawdzi całe drzewo produktu (BOM) i pokaże:**
- ✅ Czy masz wystarczającą ilość wszystkich składników.
- ⚠️ Czego brakuje i (jeśli dane są w systemie) kiedy planowana jest dostawa.
- 🔄 **Inteligentne Zamienniki**: Jeśli brakuje składnika X, a w systemie zdefiniowano zamiennik Y o wystarczającym stanie, system zasugeruje jego użycie.

#### 3. Raport Krytycznych Braków
Lista surowców, które kończą się najszybciej w stosunku do średniego zużycia tygodniowego (tzw. *Coverage*). Możliwe jest wygenerowanie wyjaśnienia przyczyn braków przez AI.

---

### Moduł: AI Assistant

Inteligentny asystent zakupowy wykorzystujący Generatywną Sztuczną Inteligencję (GenAI).

> 💡 **Prywatność**: System obsługuje lokalne modele LLM (np. Qwen2.5), co gwarantuje, że Twoje dane firmowe nie trafiają do chmury. W przypadku modeli chmurowych (Gemini, OpenRouter), dane są anonimizowane.

#### Tryby Analizy:

1. **Analiza Surowca (Anomalie)**
   - Wybierz surowiec z listy.
   - AI przeanalizuje jego historię zużycia i obecny stan magazynowy.
   - Otrzymasz informację o trendzie, pokryciu zapasami (coverage) oraz sugestię czy należy zwiększyć zapasy.

2. **Analiza Wyrobu Gotowego (BOM)**
   - Wybierz wyrób gotowy i podaj planowaną ilość produkcji.
   - AI przeanalizuje cały BOM (listę materiałową) pod kątem dostępności składników.
   - System sprawdzi również dostępność surowców na **innych magazynach** i zasugeruje ewentualne przesunięcia międzymagazynowe.
   - Otrzymasz raport zakupowy ze wskazaniem krytycznych ryzyk dla ciągłości produkcji.

#### Funkcje Zaawansowane (Administrator):
- **Wybór silnika AI**: Możliwość przełączania między Ollama, Local LLM, Google Gemini, OpenRouter.
- **Tryb Porównania (Benchmark)**: Możliwość uruchomienia analizy na dwóch modelach jednocześnie (np. Qwen2.5 vs Mistral), aby porównać jakość rekomendacji.

---

## Panel Administracyjny

(Dostępny tylko dla Administratorów)

1. **Użytkownicy**:
   - Tworzenie nowych użytkowników.
   - Resetowanie haseł.
   - Przypisywanie ról (Admin/User).
2. **Modele AI**:
   - **Pobieranie**: Możliwość pobrania i uruchomienia lokalnych modeli językowych (format GGUF).
   - **Konfiguracja ML**: Dostrajanie parametrów (np. `learning_rate` dla modelu Gradient Boosting).
3. **Audyt**:
   - Przegląd logów systemowych (logowania, błędy, kluczowe akcje użytkowników).

---

## Rozwiązywanie Problemów

| Problem | Rozwiązanie |
|---------|-------------|
| **Brak towaru na liście** | Sprawdź filtry dat oraz czy wybrano odpowiedni magazyn. Towar musi mieć historię ruchu w zadanym okresie. |
| **Błąd połączenia z bazą** | Jeśli widzisz "🔴 Błąd połączenia", odśwież stronę (F5). Jeśli problem wraca, skontaktuj się z IT (możliwy problem z VPN lub serwerem SQL). |
| **Symulacja trwa długo** | Przy bardzo złożonych wyrobach (wielopoziomowe BOM) analiza może potrwać do 10-15 sekund. |
| **Brak modelu AI** | Jeśli Asystent zgłasza brak modelu, Administrator musi pobrać model w zakładce *Panel Admina -> Modele AI* lub upewnić się, że pliki `.gguf` znajdują się w katalogu `models/`. |

---
*Dokumentacja przygotowana dla systemu AI Supply Assistant.*
