# 🏭 AI Supply Assistant

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Inteligentny Asystent Zakupowy** dla modułu Produkcja by CTI / Comarch Optima.  
System wspiera działy zakupów i produkcji w analizie zużycia surowców, prognozowaniu popytu oraz wykrywaniu anomalii przy użyciu Sztucznej Inteligencji.

---

## ✨ Funkcjonalności

| Moduł | Opis |
|:------|:-----|
| **📊 Analiza Danych** | Wykresy trendów zużycia, Panel Zakupowca z BOM |
| **📈 Predykcja ML** | Prognoza popytu (RF, GB, Exp. Smoothing, **🧠 LSTM Deep Learning**) |
| **📉 Metryki jakości** | MAPE, RMSE, MAE, R² - ocena dokładności prognoz |
| **🤖 AI Assistant** | Analiza anomalii i rekomendacje (Gemini / Ollama / Local LLM) |
| **📥 Pobieranie modeli** | Pobieranie GGUF z HuggingFace (Qwen, Llama, Mistral, Phi-3) |
| **🌐 Deployment sieciowy** | Obsługa wielu użytkowników w sieci LAN |
| **⚙️ Konfiguracja ML** | Panel admina do tuningu hiperparametrów modeli |
| **🏭 Filtrowanie Magazynów** | Analiza per magazyn z kontekstem w promptach AI |
| **🔐 System Użytkowników** | Logowanie, role (Admin/Zakupowiec), kontrola dostępu |
| **🔌 Kreator Połączenia** | Automatyczne wykrywanie SQL Server, łatwa konfiguracja |
| **📦 Instalator Windows** | Automatyczna instalacja i konfiguracja usługi |

---

## 🚀 Szybki Start

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/YOUR_USERNAME/ai-supply-assistant.git
cd ai-supply-assistant
```

### 2. Instalacja zależności

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Uruchomienie

```bash
streamlit run main.py
```

Aplikacja uruchomi się pod adresem: `http://localhost:8501`

### 4. Pierwsze logowanie

| Dane domyślne | Wartość |
|---------------|---------|
| Użytkownik | `admin` |
| Hasło | `admin123` |

> ⚠️ **Zmień hasło po pierwszym logowaniu!** (Panel Admina → Zmień hasło)

---

## 🔌 Kreator Połączenia (Pierwsze uruchomienie)

Przy pierwszym uruchomieniu aplikacja automatycznie uruchomi **Kreator Połączenia**:

1. **🖥️ Wykrywanie serwerów** - automatycznie znajduje lokalne instancje SQL Server
2. **🔐 Uwierzytelnianie** - SQL Auth lub Windows Auth
3. **🗄️ Wybór bazy** - lista dostępnych baz danych
4. **✅ Test połączenia** - weryfikacja i zapis do `.env`

---

## 🔐 Role i Uprawnienia

| Rola | Analiza | Predykcja | AI | Zmiana bazy | Panel Admina |
|------|:-------:|:---------:|:--:|:-----------:|:------------:|
| **Administrator** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Zakupowiec** | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## 📁 Struktura Projektu

```
ai-supply-assistant/
├── main.py                 # Entry Point (Streamlit)
├── config/
│   └── users.json          # Użytkownicy (hasła bcrypt)
├── src/
│   ├── db_connector.py     # Połączenie z MS SQL
│   ├── sql_server_discovery.py  # Wykrywanie SQL Server
│   ├── preprocessing.py    # Przetwarzanie danych
│   ├── forecasting.py      # Modele ML
│   ├── ai_engine/          # Klienci AI (Gemini, Ollama, Local LLM)
│   ├── security/
│   │   ├── auth.py         # Uwierzytelnianie i autoryzacja
│   │   └── audit.py        # Logowanie zdarzeń
│   └── gui/
│       ├── views/          # Widoki (analysis, prediction, assistant, login, admin)
│       └── components/     # Komponenty (sidebar)
├── models/                 # Modele GGUF dla Local LLM
├── notebooks/              # Jupyter Notebooks
├── CHANGELOG.md            # Historia zmian
└── requirements.txt        # Zależności Python
```

---

## 🛡️ Bezpieczeństwo

- ✅ **Uwierzytelnianie** - logowanie użytkowników z hashowaniem bcrypt
- ✅ **Autoryzacja** - role-based access control (RBAC)
- ✅ **Parametryzowane zapytania SQL** - ochrona przed SQL Injection
- ✅ **Anonimizacja danych** - NIP, PESEL, email przed wysyłką do chmury
- ✅ **Lokalny tryb AI** - pełna prywatność danych
- ✅ **Zmienne środowiskowe** - wrażliwe dane w `.env`

---

## 📖 Dokumentacja

- [Instrukcja Użytkownika](USER_GUIDE.md) - Przewodnik dla użytkowników końcowych
- [Dokumentacja Techniczna](TECHNICAL_DOCUMENTATION.md) - Architektura i API
- [Historia Zmian](CHANGELOG.md) - Changelog projektu
- [Prezentacja Akademicka](notebooks/prezentacja_akademicka.ipynb) - Jupyter Notebook z demonstracją projektu

---

## 🎓 Kontekst Akademicki

Projekt realizowany w ramach studiów podyplomowych **"Analiza Danych - Data Science z elementami AI"** na Uniwersytecie WSB Merito Chorzów.

Projekt demonstruje praktyczne zastosowanie technik omawianych w programie studiów:

- Python i biblioteki Data Science (pandas, numpy, scikit-learn)
- Eksploracyjna Analiza Danych (EDA)
- Machine Learning (Random Forest, Gradient Boosting, Time Series)
- Sztuczna Inteligencja (LLM, Prompt Engineering)

---

## 🤝 Współpraca

1. Fork repozytorium
2. Stwórz branch (`git checkout -b feature/nowa-funkcja`)
3. Commit (`git commit -m 'Dodano nową funkcję'`)
4. Push (`git push origin feature/nowa-funkcja`)
5. Otwórz Pull Request

---

## 📄 Licencja

Ten projekt jest licencjonowany na warunkach [MIT License](LICENSE).

---

## 👤 Autor

**Artur Kozłowski** - Projekt Zaliczeniowy  
Studia podyplomowe: *Analiza Danych - Data Science z elementami AI*  
Uniwersytet WSB Merito Chorzów  
*2025-2026*
