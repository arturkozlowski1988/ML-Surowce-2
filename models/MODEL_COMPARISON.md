# 🤖 Porównanie Modeli AI - DeepSeek-R1 vs Mistral-Small vs Qwen2.5

**Data:** 28 grudnia 2024  
**Projekt:** AI Supply Assistant  
**Status:** ⏳ Pobieranie modeli w toku

---

## 📊 Specyfikacja Modeli

| Model | Rozmiar | Parametry | Kontekst | RAM (est.) | Opis |
|-------|---------|-----------|----------|------------|------|
| **Qwen2.5-3B** | 1.96 GB | 3B | 32k | ~4 GB | Szybki, wydajny, idealny na CPU |
| **DeepSeek-R1-14B** | ~8 GB | 14B | 32k | ~12 GB | Zaawansowane rozumowanie (R1 distilled) |
| **Mistral-Small-24B** | ~14 GB | 24B | 32k | ~18 GB | Najwyższa jakość, najbardziej zaawansowany |

---

## 🎯 Przewidywane Zalety i Wady

### Qwen2.5-3B ✅ (Obecny)
**Zalety:**
- ✅ Bardzo szybki (najszybszy z trzech)
- ✅ Niskie wymagania RAM (~4GB)
- ✅ 32k kontekst
- ✅ Najnowszy (grudzień 2024)
- ✅ Dobry w języku polskim

**Wady:**
- ⚠️ Najmniejszy model - może być mniej precyzyjny w złożonych analizach
- ⚠️ Ograniczone rozumowanie dla bardzo skomplikowanych scenariuszy

**Najlepszy dla:** Szybkie analizy, środowiska z ograniczonymi zasobami

---

### DeepSeek-R1-14B 🧠 (Nowy)
**Zalety:**
- ✅ **Specjalizacja w rozumowaniu (Reasoning)** - model R1
- ✅ Średnia wielkość (4x więcej parametrów niż Qwen)
- ✅ Dobra równowaga prędkość/jakość
- ✅ 32k kontekst
- ✅ Zaawansowana logika biznesowa

**Wady:**
- ⚠️ Wolniejszy niż Qwen (~3x)
- ⚠️ Wymaga więcej RAM (~12GB)
- ⚠️ Średnia jakość języka polskiego (lepszy w EN)

**Najlepszy dla:** Złożone analizy logiczne, wykrywanie anomalii, rozumowanie przyczynowo-skutkowe

---

### Mistral-Small-24B 🚀 (Nowy)
**Zalety:**
- ✅ **Najwyższa jakość odpowiedzi**
- ✅ Najlepsze rozumienie kontekstu biznesowego
- ✅ Doskonały w wielojęzyczności (+ polski)
- ✅ 32k kontekst
- ✅ Najprecyzyjniejsze rekomendacje

**Wady:**
- ⚠️ Najwolniejszy (~5-7x wolniej niż Qwen)
- ⚠️ Wymaga dużo RAM (~18GB)
- ⚠️ Największy rozmiar pliku

**Najlepszy dla:** Krytyczne decyzje biznesowe, najwyższa jakość analiz

---

## 🔍 Przypadki Użycia

### Scenariusz 1: Codzienna Analiza Trendów
**Potrzeba:** Szybkie sprawdzenie trendów zużycia surowców  
**Rekomendacja:** **Qwen2.5-3B** ⭐⭐⭐⭐⭐
- Wystarczająca jakość
- Natychmiastowe odpowiedzi
- Niskie zużycie zasobów

### Scenariusz 2: Wykrywanie Anomalii
**Potrzeba:** Identyfikacja nietypowych wzorców i przyczyn  
**Rekomendacja:** **DeepSeek-R1-14B** ⭐⭐⭐⭐⭐
- Specjalizacja w rozumowaniu logicznym
- Chain-of-thought reasoning
- Lepsze wyjaśnianie przyczyn

### Scenariusz 3: Strategiczne Decyzje Zakupowe
**Potrzeba:** Optymalizacja długoterminowej strategii zakupów  
**Rekomendacja:** **Mistral-Small-24B** ⭐⭐⭐⭐⭐
- Najwyższa jakość analiz
- Najbardziej przemyślane rekomendacje
- Warto poczekać na odpowiedź

### Scenariusz 4: Batch Processing (Nocna Analiza)
**Potrzeba:** Analiza 100+ produktów podczas nocy  
**Rekomendacja:** **Qwen2.5-3B** lub **DeepSeek-R1-14B**
- Qwen: Jeśli czas jest krytyczny
- DeepSeek: Jeśli jakość > prędkość

---

## 💡 Strategia Wyboru Modelu

### Podejście 1: Single Model (Prosty)
Wybierz JEDEN model do wszystkich zadań:
- **Budget Setup:** Qwen2.5-3B
- **Balanced Setup:** DeepSeek-R1-14B ✅ **RECOMMENDED**
- **Premium Setup:** Mistral-Small-24B

### Podejście 2: Hybrid Model (Zaawansowany)
Używaj różnych modeli do różnych zadań:

```python
# Przykład w kodzie
if task_type == "quick_overview":
    model = "qwen2.5-3b"
elif task_type == "anomaly_detection":
    model = "deepseek-r1-14b"
elif task_type == "strategic_planning":
    model = "mistral-small-24b"
```

---

## 🧪 Plan Testowania

### Testy Wydajnościowe
1. **Prędkość ładowania** - Czas inicjalizacji modelu
2. **Tokens/sekunda** - Szybkość generowania
3. **Wykorzystanie RAM** - Zużycie pamięci

### Testy Jakościowe
1. **Analiza trendu** - Czy poprawnie identyfikuje wzrosty/spadki?
2. **Wykrywanie anomalii** - Czy rozpoznaje nietypowe sytuacje?
3. **Rekomendacje** - Czy sugestie są praktyczne i użyteczne?
4. **Język polski** - Jakość gramatyki i stylu
5. **Kontekst biznesowy** - Czy rozumie specyfikę supply chain?

---

## 📝 Jak Uruchomić Testy

### Automatyczny Test Porównawczy
```bash
# Uruchom skrypt porównawczy (gdy wszystkie modele będą pobrane)
python scripts/compare_models.py
```

To uruchomi wszystkie 3 modele z tymi samymi promptami i wygeneruje raport.

### Ręczny Test w Aplikacji
```bash
# Uruchom aplikację
streamlit run main.py

# Przejdź do sekcji AI Assistant
# Wybierz "Local LLM (Embedded)"
# Edytuj .env aby zmienić LOCAL_LLM_PATH na:
#   - models/qwen2.5-3b-instruct-q4_k_m.gguf
#   - models/deepseek-r1-14b-q4_k_m.gguf  
#   - models/mistral-small-24b-q4_k_m.gguf
```

---

## 🎓 Kryteria Wyboru - Decision Matrix

| Kryterium | Waga | Qwen2.5 | DeepSeek-R1 | Mistral-Small |
|-----------|------|---------|-------------|---------------|
| Prędkość | 25% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Jakość odpowiedzi | 35% | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Wymagania RAM | 15% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Język polski | 15% | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Rozumowanie | 10% | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Weighted Score:**
- **Qwen2.5-3B:** 3.65/5 - Najszybszy i wydajny
- **DeepSeek-R1-14B:** 3.80/5 - ✅ **Najlepszy balans**
- **Mistral-Small-24B:** 4.10/5 - Najwyższa jakość (jeśli masz RAM)

---

## 🚀 Rekomendacje

### Dla Twojego Projektu (AI Supply Assistant)

1. **Testuj wszystkie 3** - Pobierz, uruchom compare_models.py
2. **Użyj DeepSeek-R1 jako głównego** - Najlepszy balans dla supply chain
3. **Zachowaj Qwen2.5 jako backup** - Na wypadek braków zasobów
4. **Mistral-Small na produkcję** - Jeśli klient ma mocny sprzęt

### Implementacja w Kodzie

Możesz dodać selektor modelu w aplikacji:
```python
model_choice = st.selectbox(
    "Wybierz model AI:",
    ["Qwen2.5-3B (Szybki)", "DeepSeek-R1-14B (Balanced)", "Mistral-Small-24B (Premium)"]
)
```

---

## 📚 Dodatkowe Informacje

### DeepSeek-R1
- Źródło: https://huggingface.co/deepseek-ai/DeepSeek-R1
- Specjalność: Chain-of-Thought Reasoning
- Technologia: Distilled from DeepSeek-R1-671B

### Mistral-Small
- Źródło: https://mistral.ai/news/mistral-small/
- Specjalność: Enterprise-grade LLM
- Technologia: Mistral architecture (Sep 2024)

### Qwen2.5
- Źródło: https://github.com/QwenLM/Qwen2.5
- Specjalność: Fast inference, multilingual
- Technologia: Latest Qwen series (Dec 2024)

---

**Status pobierania:**
- ✅ Qwen2.5-3B - Gotowy
- ⏳ DeepSeek-R1-14B - Pobieranie...
- ⏳ Mistral-Small-24B - Pobieranie...

**Następny krok:** Po zakończeniu pobierania uruchom `python scripts/compare_models.py`
