# 📖 Instrukcja Obsługi: AI Supply Assistant

> **Wersja**: 1.5.0  
> **Data aktualizacji**: 2026-01-10

---

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Instalacja i Konfiguracja](#instalacja-i-konfiguracja)
3. [Logowanie i Role Użytkowników](#logowanie-i-role-użytkowników)
4. [Moduł: Analiza Danych](#moduł-analiza-danych)
5. [Moduł: Predykcja ML](#moduł-predykcja-ml)
6. [Moduł: AI Assistant](#moduł-ai-assistant)
7. [Moduł: MRP Lite](#moduł-mrp-lite)
8. [Panel Administracyjny](#panel-administracyjny)
9. [Rozwiązywanie Problemów](#rozwiązywanie-problemów)

---

## Wprowadzenie

**AI Supply Assistant** to inteligentny system wspierający działy zakupów i produkcji w:

- 📊 Analizie historycznego zużycia surowców
- 📈 Prognozowaniu przyszłego zapotrzebowania (Machine Learning)
- 🤖 Wykrywaniu anomalii i generowaniu rekomendacji (AI/LLM)
- 🏭 Planowaniu produkcji i zarządzaniu BOM

System integruje się z bazami danych **Comarch Optima / Produkcja by CTI**.

---

## Instalacja i Konfiguracja

### Opcja 1: Automatyczny instalator (zalecane)

```batch
# Uruchom jako Administrator
install.bat
```

Instalator automatycznie:

- Sprawdzi wymagania (Python, ODBC Driver)
- Zainstaluje zależności
- Skonfiguruje firewall
- Zainstaluje usługę Windows

### Opcja 2: Ręczna instalacja

```bash
# 1. Zainstaluj zależności
pip install -r requirements.txt

# 2. Skopiuj i skonfiguruj plik .env
copy .env.example .env
notepad .env

# 3. Uruchom aplikację
streamlit run main.py
```

### Konfiguracja bazy danych (.env)

```ini
# Połączenie z SQL Server
DB_CONN_STR=mssql+pyodbc://user:password@SERVER\INSTANCE/database?driver=ODBC+Driver+17+for+SQL+Server

# API AI (opcjonalnie)
GEMINI_API_KEY=your_api_key

# Model lokalny (opcjonalnie)
LOCAL_LLM_PATH=models/qwen2.5-7b-instruct-q4_k_m.gguf
```

### Uruchomienie sieciowe (LAN)

Dla dostępu z innych komputerów w sieci:

```batch
start_server.bat
```

Użytkownicy łączą się przez: `http://192.168.x.x:8501`

---

## Logowanie i Role Użytkowników

### Dane domyślne

| Użytkownik | Hasło | Rola |
|------------|-------|------|
| admin | admin123 | Administrator |

> ⚠️ **Zmień hasło natychmiast po pierwszym logowaniu!**

### Role i uprawnienia

| Funkcja | Administrator | Zakupowiec |
|---------|:-------------:|:----------:|
| Analiza Danych | ✅ | ✅ |
| Predykcja ML | ✅ | ✅ |
| AI Assistant | ✅ | ✅ |
| MRP Lite | ✅ | ✅ |
| Zmiana bazy danych | ✅ | ❌ |
| Panel Admina | ✅ | ❌ |
| Pobieranie modeli | ✅ | ❌ |
| Konfiguracja ML | ✅ | ❌ |

---

## Moduł: Analiza Danych

Główny ekran analityczny do przeglądania historii zużycia surowców.

### Jak używać

1. **Wybierz tryb** "Analiza Danych" w menu bocznym
2. **Ustaw zakres dat** w filtrach
3. **Wybierz magazyny** (opcjonalnie)
4. **Wybierz surowce** z listy (wyszukaj po nazwie lub kodzie)

### Panel Zakupowca

Po wybraniu **pojedynczego surowca** pojawia się rozszerzony panel:

- **Wykres "Gdzie używany"**: Top 20 wyrobów gotowych używających tego surowca
- **Tabela BOM**: Wybierz wyrób, aby zobaczyć pełną recepturę
- **Statystyki**: Średnie zużycie, trendy, sezonowość

---

## Moduł: Predykcja ML

Moduł prognozowania przyszłego zapotrzebowania z wykorzystaniem Machine Learning.

### Dostępne modele

| Model | Opis | Kiedy używać |
|-------|------|--------------|
| **Baseline (SMA-4)** | Średnia z 4 tygodni | Punkt odniesienia |
| **Random Forest** | Ensemble drzew decyzyjnych | Uniwersalny, dobry start |
| **Gradient Boosting** | Sekwencyjne uczenie | Wysokiej dokładności |
| **Exponential Smoothing** | Holt-Winters | Silna sezonowość |
| **🧠 LSTM Deep Learning** | Sieć neuronowa | Złożone wzorce czasowe |

### Jak używać

1. Wybierz tryb **"Predykcja"**
2. Wybierz surowiec
3. Wybierz model predykcyjny
4. Kliknij **"Analizuj"**

### Interpretacja wyników

Po wygenerowaniu prognozy zobaczysz:

- **Wykres**: Historia + prognoza 4 tygodnie w przód
- **Metryki jakości**:
  - **MAPE** (%)**: Średni błąd procentowy (im niższy, tym lepiej)
  - **RMSE**: Odchylenie standardowe błędu
  - **MAE**: Średni błąd bezwzględny
  - **R²**: Współczynnik determinacji (1.0 = idealne dopasowanie)

> 💡 **Wskazówka**: MAPE < 20% to dobry wynik dla prognoz zakupowych

---

## Moduł: AI Assistant

Inteligentny asystent wykorzystujący modele językowe (LLM) do analizy danych.

### Dostępne silniki AI

| Silnik | Lokalizacja | Uwagi |
|--------|-------------|-------|
| **Google Gemini** | Chmura | Szybki, wymaga API key |
| **OpenRouter** | Chmura | 100+ modeli, wymaga API key |
| **Ollama** | Lokalny serwer | Wymaga uruchomionej Ollama |
| **Local LLM** | Wbudowany | Offline, wymaga modelu GGUF |

### Tryby analizy

#### 1. Analiza Surowca (Anomalie)

AI analizuje historię zużycia i wykrywa:

- Nietypowe skoki/spadki
- Zmiany trendów
- Potencjalne problemy z dostawami

#### 2. Analiza Wyrobu Gotowego (BOM)

Dla planowania produkcji:

1. Wybierz wyrób gotowy
2. Podaj planowaną ilość
3. AI sprawdzi stan składników i wygeneruje listę zakupową

### Porównanie modeli

Funkcja umożliwia porównanie odpowiedzi różnych modeli AI na to samo pytanie.

---

## Moduł: MRP Lite

Uproszczone planowanie zapotrzebowania materiałowego.

### Funkcje

- **Symulacja produkcji**: Sprawdź dostępność składników
- **Wykrywanie braków**: Lista brakujących surowców
- **Sugestie zamówień**: Rekomendowane ilości do zakupu

---

## Panel Administracyjny

Dostępny tylko dla użytkowników z rolą Administrator.

### Zakładki

#### 📊 Dashboard

Statystyki systemu, KPI, aktywność użytkowników.

#### 👥 Użytkownicy

- Dodawanie/usuwanie użytkowników
- Zmiana haseł
- Przypisywanie ról

#### 🤖 Ustawienia LLM

- Wybór domyślnego silnika AI
- Konfiguracja parametrów modeli

#### 📥 Pobieranie Modeli

**Zarządzanie modelami LLM z HuggingFace Hub**

1. **Zainstalowane modele**: Lista pobranych modeli z opcją usunięcia
2. **Dostępne modele**:
   - ⭐ Qwen2.5-7B (zalecany, 4.7 GB)
   - Qwen2.5-3B (2.0 GB)
   - Llama 3.2-3B (2.0 GB)
   - Mistral-7B (4.4 GB)
   - Phi-3 Mini (2.4 GB)
3. **Niestandardowe modele**: Pobierz dowolny model GGUF

> 💡 **Zalecenie**: Qwen2.5-7B oferuje najlepszą obsługę języka polskiego

#### ⚙️ Konfiguracja ML

**Tuning hiperparametrów modeli**

| Model | Parametry |
|-------|-----------|
| Random Forest | Liczba drzew, głębokość, min. próbek |
| Gradient Boosting | Learning rate, estymatory, głębokość |
| LSTM | Neurony, epoki, dropout, okno historyczne |

#### 🗄️ Uprawnienia Baz

Konfiguracja dostępu do baz danych.

#### 🔔 Alerty

Konfiguracja powiadomień i alertów.

#### 📝 Edycja Promptów

Dostosowywanie promptów dla AI Assistant.

#### 📋 Audyt

Przegląd logów bezpieczeństwa.

#### 🔧 Ustawienia Systemowe

Konfiguracja globalna aplikacji.

---

## Rozwiązywanie Problemów

### Błąd połączenia z bazą danych

```
❌ Nie można połączyć się z bazą danych
```

**Rozwiązania**:

1. Sprawdź czy SQL Server jest uruchomiony
2. Sprawdź connection string w `.env`
3. Sprawdź firewall (port 1433)
4. Sprawdź uprawnienia użytkownika SQL

### Brak modelu LLM

```
⚠️ Brak modelu lokalnego
```

**Rozwiązanie**:

1. Panel Admina → "📥 Pobieranie Modeli"
2. Pobierz zalecany model (Qwen2.5-7B)
3. Poczekaj na zakończenie pobierania (~5 min dla 5GB)

### LSTM niedostępny

```
⚠️ TensorFlow nie jest zainstalowany
```

**Rozwiązanie**:

```bash
pip install tensorflow>=2.15.0
```

### Użytkownicy nie mogą się połączyć przez sieć

**Rozwiązania**:

1. Sprawdź czy serwer nasłuchuje: `netstat -an | findstr 8501`
2. Sprawdź firewall: port 8501 musi być otwarty
3. Użyj `start_server.bat` zamiast `run_app.bat`

### Wolne działanie prognoz

**Rozwiązania**:

1. Użyj mniejszego zakresu dat
2. Panel Admina → Konfiguracja ML → zmniejsz liczbę drzew/estymatorów
3. Dla LSTM: zmniejsz liczbę epok

---

## Skróty klawiszowe

| Skrót | Akcja |
|-------|-------|
| Ctrl+K | Wyszukiwanie (Streamlit) |
| R | Odświeżenie (w przeglądarce) |

---

## Wsparcie techniczne

W przypadku problemów:

1. Sprawdź logi w folderze `logs/`
2. Sprawdź sekcję "Rozwiązywanie Problemów" powyżej
3. Skontaktuj się z administratorem systemu

---

*AI Supply Assistant v1.5.0 © 2026*
