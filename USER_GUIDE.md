# Instrukcja Użytkownika: AI Supply Assistant (Produkcja by CTI)

## Spis Treści

1. [Wstęp i Uruchomienie](#wstęp-i-uruchomienie)
2. [Moduł 1: Analiza Danych i Panel Zakupowca](#moduł-1-analiza-danych-i-panel-zakupowca)
3. [Moduł 2: Predykcja Zapotrzebowania](#moduł-2-predykcja-zapotrzebowania)
4. [Moduł 3: Inteligentny Asystent (GenAI)](#moduł-3-inteligentny-asystent-genai)
5. [Rozwiązywanie Problemów](#rozwiązywanie-problemów)

---

## Wstęp i Uruchomienie

System **AI Supply Assistant** wspiera działy zakupów i produkcji w analizie zużycia surowców, prognozowaniu popytu oraz wykrywaniu anomalii przy użyciu Sztucznej Inteligencji.

### Wymagania

- System Windows
- Zainstalowany Python 3.9+
- Dostęp do bazy danych MS SQL (Optima / XL / CTI)
- (Opcjonalnie) Zainstalowana Ollama dla modelu lokalnego

### Uruchomienie aplikacji

1. Otwórz terminal w folderze projektu.
2. Uruchom komendę:

   ```powershell
   streamlit run main.py
   ```

3. Aplikacja otworzy się automatycznie w przeglądarce pod adresem `http://localhost:8501`.

---

## Moduł 1: Analiza Danych i Panel Zakupowca

Główny ekran analityczny.

1. **Wybór Surowca**: W menu bocznym ustaw zakres dat. W polu "Wybierz surowce do wykresu" wyszukaj interesujący Cię materiał.
2. **Wykres Trendu**: Zobaczysz historię zużycia w ujęciu tygodniowym.
3. **Panel Zakupowca**:
   - Po wybraniu **pojedynczego** surowca, na dole strony pojawi się sekcja "Kontekst Produkcyjny".
   - **Wykres "Gdzie używany..."**: Pokazuje Top 20 wyrobów gotowych, do których produkcji użyto tego surowca.
   - **Tabela BOM**: Wybierz wyrób z listy, aby zobaczyć jego pełną recepturę (drzewo produktowe).

---

## Moduł 2: Predykcja Zapotrzebowania

Moduł służący do planowania przyszłych zakupów.

1. Przełącz tryb w menu bocznym na **"Predykcja"**.
2. Wybierz surowiec.
3. **Wybierz Model Predykcyjny**:
   - **Baseline (SMA-4)**: Prosta średnia z ostatnich 4 tygodni. Dobra jako punkt odniesienia.
   - **Random Forest**: Model AI uczący się nieliniowych zależności. Dobry uniwersalny wybór.
   - **Gradient Boosting**: Model AI o wysokiej precyzji. Wybierz, jeśli masz dużo danych historycznych.
   - **Exponential Smoothing**: Klasyczna statystyka (Holt-Winters). Najlepsza, jeśli zużycie ma wyraźny sezonowy charakter (np. rośnie latem).
4. Kliknij "Analizuj". System wygeneruje wykres prognozy na 4 tygodnie w przód.

---

## Moduł 3: Inteligentny Asystent (GenAI)

Twój osobisty analityk danych.

1. Przełącz tryb na **"AI Assistant (GenAI)"**.
2. **Wybierz Silnik AI**:
   - **Google Gemini**: Szybki, działa w chmurze. (Dane są anonimizowane).
   - **Ollama (Local)**: Działa na Twoim komputerze. Pełna prywatność.
3. **Wybierz Tryb Analizy**:
   - **Analiza Surowca (Anomalie)**: Wybierz surowiec. AI przeanalizuje ostatnie tygodnie i powie, czy trend jest niepokojący i dlaczego.
   - **Analiza Wyrobu Gotowego (BOM)**: Wybierz produkt, który chcesz wyprodukować (np. 100 szt.). AI sprawdzi stan magazynowy wszystkich składników i stworzy listę zakupową brakujących elementów.

---

## Rozwiązywanie Problemów

- **Błąd połączenia z bazą**: Sprawdź ustawienia w sekcji "Konfiguracja" w menu bocznym. Upewnij się, że VPN jest włączony (jeśli wymagany).
- **Błąd Ollama**: Upewnij się, że masz uruchomioną usługę Ollama (`ollama serve`) i pobrany model (`ollama pull llama3.2`).
- **Brak danych**: Niektóre surowce mogą nie mieć historii zużycia w wybranym okresie. Zmień daty w filtrach.
