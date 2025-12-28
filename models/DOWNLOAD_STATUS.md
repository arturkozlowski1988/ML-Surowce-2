# 🤖 Konfiguracja Modeli LLM - AI Supply Assistant

**Status:** ✅ Gotowe do użycia  
**Data:** 28 grudnia 2024

---

## 📦 Dostępne Modele

| Model | Rozmiar | Prędkość | Zastosowanie |
|-------|---------|----------|--------------|
| **Qwen2.5-7B** ⭐ | 3.55 GB | ~3.5 w/s | Domyślny - zbalansowany |
| **Qwen2.5-3B** | 1.96 GB | ~6 w/s | Szybki backup |

---

## ⚙️ Konfiguracja

Aktywny model w `.env`:

```env
LOCAL_LLM_PATH=models/qwen2.5-7b-instruct-q3_k_m.gguf
```

### Zmiana na szybszy model 3B

```env
LOCAL_LLM_PATH=models/qwen2.5-3b-instruct-q4_k_m.gguf
```

---

## 🧪 Testowanie

```bash
python scripts/compare_models.py
```

Szczegółowe porównanie modeli: [MODEL_COMPARISON.md](MODEL_COMPARISON.md)
