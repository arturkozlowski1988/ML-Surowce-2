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
   - [Analiza Danych (Historie Zużycia)](#moduł-analiza-danych)
   - [Predykcja Popytu (ML)](#moduł-predykcja-ml)
   - [Inteligentny Asystent (AI/LLM)](#moduł-ai-assistant)
   - [MRP Lite (Symulacja Produkcji)](#moduł-mrp-lite)
5. [Panel Administracyjny](#panel-administracyjny)
6. [Rozwiązywanie Problemów](#rozwiązywanie-problemów)

---

## Wprowadzenie

**AI Supply Assistant** to zaawansowane narzędzie wspierające działy zakupów i produkcji. System integruje się z Twoim oprogramowaniem ERP (Comarch Optima / CTI), aby pomagać w podejmowaniu lepszych decyzji zakupowych.

**Co zyskujesz?**
- 📉 Mniejsze ryzyko przestojów dzięki predykcji braków.
- 💰 Optymalizację stanów magazynowych (nie kupujesz "na zapas").
- ⏱️ Oszczędność czasu przy analizie BOM (AI robi to za Ciebie).

---

## Szybki Start

### Uruchomienie aplikacji

Jeśli aplikacja jest zainstalowana na serwerze, otwórz przeglądarkę (Chrome, Edge, Firefox) i wpisz adres podany przez administratora IT, np.:

```
http://192.168.1.100:8501
```

### Pierwsze kroki

1. Zaloguj się swoimi danymi.
2. W menu bocznym (po lewej) wybierz moduł, który Cię interesuje.
3. Skorzystaj z filtrów daty i magazynów, aby zawęzić dane.

---

## Logowanie i Uprawnienia

| Rola | Dostępne funkcje |
|------|------------------|
| **Administrator** | Pełny dostęp, zarządzanie użytkownikami, konfiguracja AI i baz danych. |
| **Zakupowiec** | Analiza, Predykcja, AI Assistant, MRP Lite. Brak dostępu do ustawień systemowych. |

> 🔒 **Bezpieczeństwo**: Po pierwszym logowaniu zmień hasło klikając w swój profil lub prosząc administratora.

---

## Główne Moduły

### Moduł: Analiza Danych

Tu sprawdzisz historię. Jak zmieniało się zużycie surowców w czasie?

1. **Filtrowanie**: Ustaw zakres dat w panelu bocznym.
2. **Wybór surowców**: Wybierz jeden lub więcej surowców z listy (posortowane wg zużycia).
3. **Wykres**: Zobaczysz trend zużycia.
4. **Panel Zakupowca** (po wybraniu 1 surowca):
   - **Gdzie używany?**: Lista wyrobów gotowych, do których wchodzi ten surowiec.
   - **BOM**: Podgląd receptury wyrobu.

---

### Moduł: Predykcja ML

Tu spojrzysz w przyszłość. Ile towaru będziemy potrzebować za miesiąc?

1. Wybierz surowiec.
2. Wybierz model (algorytm):
   - **Random Forest / Gradient Boosting**: Najlepsze do ogólnych prognoz.
   - **LSTM (Deep Learning)**: Dla złożonych wzorców.
   - **Exponential Smoothing**: Jeśli występuje silna sezonowość.
3. Kliknij **Analizuj**.

**Wynik**: Wykres z prognozą na 4 tygodnie w przód oraz ocena wiarygodności prognozy (MAPE - im mniej, tym lepiej).

---

### Moduł: AI Assistant

Twój wirtualny doradca. Zadawaj pytania o dane.

**Dwa tryby pracy:**
1. **Analiza Surowca (Anomalie)**: AI sprawdzi historię zużycia i podpowie, czy trend jest niepokojący (np. nagły wzrost zużycia) oraz czy obecny stan magazynowy jest bezpieczny.
2. **Analiza Wyrobu Gotowego (BOM)**: Planujesz produkcję? AI przeanalizuje całą recepturę (drzewo BOM), sprawdzi stany wszystkich składników na magazynach i wygeneruje listę zakupową.

> 💡 **Wskazówka**: Jeśli korzystasz z **Local LLM**, Twoje dane nie opuszczają firmy (pełna prywatność).

---

### Moduł: MRP Lite

Symulator produkcji i wykrywanie braków w czasie rzeczywistym.

#### 1. Panel Produkcyjny CTI
Na górze widoczne są wskaźniki na żywo z systemu produkcyjnego:
- **Aktywne Zlecenia**: Ile zleceń jest w toku.
- **Dokumenty Braków**: Ile dokumentów sygnalizuje braki.
- **Technologie**: Liczba aktywnych technologii.
- **Zasoby**: Dostępne zasoby produkcyjne.

#### 2. Symulacja "Co-Jeśli"
Chcesz sprawdzić, czy wyprodukujesz 500 sztuk wyrobu X?
1. Wybierz wyrób.
2. Wpisz ilość.
3. Kliknij **Uruchom Symulację**.

**Wynik**:
- ✅ **MOŻLIWA PRODUKCJA**: Masz wszystko.
- ⚠️ **BRAKI**: System pokaże, czego brakuje i kiedy najwcześniej to dostaniesz (jeśli zdefiniowano czasy dostaw).
- 💡 **Inteligentne Zamienniki**: Jeśli brakuje składnika głównego, a w systemie zdefiniowano zamienniki, MRP zasugeruje ich użycie, aby uratować produkcję.

#### 3. Krytyczne Braki
Tabela pokazująca surowce, które "schodzą" najszybciej i których zapas jest krytycznie niski w stosunku do średniego zużycia.

---

## Panel Administracyjny

(Tylko dla Administratorów)

- **Użytkownicy**: Dodawanie kont i reset haseł.
- **Pobieranie Modeli**: Zarządzanie lokalnymi modelami AI (GGUF). Zalecany model: `Qwen2.5-7B`.
- **Konfiguracja ML**: Dostrajanie parametrów algorytmów predykcji.
- **Audyt**: Przegląd logów bezpieczeństwa (kto, co, kiedy).

---

## Rozwiązywanie Problemów

**❓ Nie widzę surowca na liście.**
Sprawdź, czy surowiec ma typ "Towar" w Comarch Optima i czy był używany w wybranym zakresie dat.

**❓ Symulacja trwa długo.**
Przy skomplikowanych wyrobach (wielopoziomowe BOM) analiza może potrwać kilka sekund. Cierpliwości.

**❓ Błąd "Brak modelu lokalnego".**
Poproś administratora o pobranie modelu w Panelu Admina -> Pobieranie Modeli.

**❓ Prognoza jest niedokładna.**
Spróbuj zmienić model (np. z Random Forest na Exponential Smoothing) lub zwiększ zakres danych historycznych.

---
*Dziękujemy za używanie AI Supply Assistant!*
