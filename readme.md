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
| **📈 Predykcja** | Prognoza popytu (Random Forest, Gradient Boosting, Exp. Smoothing) |
| **🤖 AI Assistant** | Analiza anomalii i rekomendacje zakupowe (Gemini / Ollama) |

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

### 3. Konfiguracja

Skopiuj plik `.env.example` do `.env` i uzupełnij dane:

```bash
copy .env.example .env
```

Edytuj `.env`:

- `DB_CONN_STR` - connection string do MS SQL
- `GEMINI_API_KEY` - klucz API Google Gemini (opcjonalnie)
- `LOCAL_LLM_PATH` - ścieżka do modelu GGUF (opcjonalnie, dla lokalnego AI)

**NOWE: Lokalny Model AI (Grudzień 2024)**
```bash
# Model: Qwen2.5-3B-Instruct (Zalecany - najnowszy, 32k kontekst)
LOCAL_LLM_PATH=models/qwen2.5-3b-instruct-q4_k_m.gguf
```
Model już skonfigurowany i gotowy do użycia! 🚀

### 4. Uruchomienie

```bash
streamlit run main.py
```

Aplikacja uruchomi się pod adresem: `http://localhost:8501`

---

## 📁 Struktura Projektu

```
ai-supply-assistant/
├── main.py                 # Entry Point (Streamlit)
├── src/
│   ├── db_connector.py     # Połączenie z MS SQL
│   ├── preprocessing.py    # Przetwarzanie danych
│   ├── forecasting.py      # Modele ML
│   └── ai_engine/          # Klienci AI (Gemini, Ollama)
├── notebooks/              # Jupyter Notebooks
├── scripts/                # Skrypty testowe
├── USER_GUIDE.md           # Instrukcja użytkownika
├── CHANGELOG.md            # Historia zmian
└── requirements.txt        # Zależności Python
```

---

## 🛡️ Bezpieczeństwo

- ✅ Parametryzowane zapytania SQL (ochrona przed SQL Injection)
- ✅ Anonimizacja danych (NIP, PESEL, email) przed wysyłką do chmury
- ✅ Lokalny tryb AI (Ollama) dla pełnej prywatności
- ✅ Zmienne środowiskowe dla wrażliwych danych

---

## 📖 Dokumentacja

- [Instrukcja Użytkownika](USER_GUIDE.md)
- [Historia Zmian](CHANGELOG.md)
- [Demo Notebook](notebooks/demo_walkthrough.ipynb)

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

**Projekt Dyplomowy** - Inteligentny Asystent Zakupowy  
*2024-2025*
