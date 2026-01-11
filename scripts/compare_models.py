"""
Model Comparison Script for AI Supply Assistant.
Compares performance of Qwen2.5-3B, DeepSeek-R1-14B, and Mistral-Small-24B.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_engine.local_llm import LocalLLMEngine

# Test prompts for supply chain analysis
TEST_PROMPTS = [
    {
        "name": "Analiza Trendu Zużycia",
        "prompt": """Przeanalizuj następujące dane zużycia surowca:

Surowiec: STAL 316L
Trend: Wzrost o 35% w ostatnich 3 miesiącach
Średnie zużycie: 2500 kg/miesiąc
Obecne zużycie: 3375 kg/miesiąc
Dni do wyczerpania zapasu: 12 dni

Podaj analizę i rekomendacje dla działu zakupów.""",
    },
    {
        "name": "Wykrywanie Anomalii",
        "prompt": """Wykryto anomalię w zużyciu surowca:

Surowiec: Farba EPOKSYDOWA RAL 7035
Normalne zużycie: 50 litrów/tydzień
Obecne zużycie: 180 litrów/tydzień (260% normy)
Trend: Gwałtowny wzrost od 2 tygodni

Co może być przyczyną i jak zareagować?""",
    },
    {
        "name": "Optymalizacja Zakupów",
        "prompt": """Przeanalizuj strategię zakupową dla następujących surowców:

1. Aluminium AL6082: lead time 4 tygodnie, zużycie stabilne
2. Guma NBR: lead time 2 tygodnie, zużycie zmienne (+/- 40%)
3. Plastik PVC: lead time 6 tygodni, zużycie rosnące (trend +15%/m-c)

Zaproponuj optymalną strategię zamawiania.""",
    },
]


def test_model(model_name: str, model_path: str, n_ctx: int = 4096):
    """Test single model with all prompts."""
    print(f"\n{'='*80}")
    print(f"Testing: {model_name}")
    print(f"Path: {model_path}")
    print(f"Context: {n_ctx}")
    print(f"{'='*80}\n")

    if not Path(model_path).exists():
        print(f"❌ Model file not found: {model_path}")
        return None

    # Initialize engine
    print("Loading model...")
    start_load = time.time()
    engine = LocalLLMEngine(model_path=model_path, n_ctx=n_ctx, verbose=False)

    # Test initialization
    if not engine._initialize():
        print(f"❌ Failed to initialize: {engine._init_error}")
        return None

    load_time = time.time() - start_load
    print(f"✅ Model loaded in {load_time:.2f}s\n")

    results = {"model": model_name, "path": model_path, "load_time": load_time, "tests": []}

    # Run test prompts
    for i, test in enumerate(TEST_PROMPTS, 1):
        print(f"\n--- Test {i}/{len(TEST_PROMPTS)}: {test['name']} ---\n")
        print(f"Prompt: {test['prompt'][:100]}...\n")

        start_gen = time.time()
        response = engine.generate_explanation(test["prompt"])
        gen_time = time.time() - start_gen

        # Count tokens (approximate)
        tokens = len(response.split())
        tokens_per_sec = tokens / gen_time if gen_time > 0 else 0

        print(f"Response ({tokens} words, {gen_time:.2f}s, {tokens_per_sec:.1f} w/s):")
        print("-" * 80)
        print(response)
        print("-" * 80)

        results["tests"].append(
            {
                "name": test["name"],
                "generation_time": gen_time,
                "word_count": tokens,
                "words_per_second": tokens_per_sec,
                "response": response,
            }
        )

        time.sleep(1)  # Cool down

    return results


def compare_models():
    """Compare available models."""
    models = [
        {"name": "Qwen2.5 3B Instruct", "path": "models/qwen2.5-3b-instruct-q4_k_m.gguf", "n_ctx": 4096},
        {"name": "Qwen2.5 7B Instruct", "path": "models/qwen2.5-7b-instruct-q3_k_m.gguf", "n_ctx": 4096},
    ]

    all_results = []

    print("\n" + "=" * 80)
    print("AI SUPPLY ASSISTANT - MODEL COMPARISON")
    print("=" * 80)
    print(f"\nTesting {len(models)} models with {len(TEST_PROMPTS)} prompts each\n")

    for model in models:
        result = test_model(model["name"], model["path"], model["n_ctx"])
        if result:
            all_results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - MODEL COMPARISON")
    print("=" * 80)

    if not all_results:
        print("No results to compare.")
        return

    # Table header
    print(f"\n{'Model':<25} {'Load Time':<12} {'Avg Gen Time':<15} {'Avg Speed':<15}")
    print("-" * 80)

    for result in all_results:
        avg_gen = sum(t["generation_time"] for t in result["tests"]) / len(result["tests"])
        avg_speed = sum(t["words_per_second"] for t in result["tests"]) / len(result["tests"])

        print(
            f"{result['model']:<25} {result['load_time']:>8.2f}s    " f"{avg_gen:>10.2f}s       {avg_speed:>10.1f} w/s"
        )

    # Quality analysis
    print("\n" + "=" * 80)
    print("QUALITY ANALYSIS")
    print("=" * 80)
    print("\nReview the responses above to assess:")
    print("✓ Accuracy and relevance for supply chain analysis")
    print("✓ Polish language quality")
    print("✓ Practical usefulness of recommendations")
    print("✓ Consistency with business context")

    # Save results
    output_file = Path("models/comparison_results.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("MODEL COMPARISON RESULTS\n")
        f.write("=" * 80 + "\n\n")

        for result in all_results:
            f.write(f"\nModel: {result['model']}\n")
            f.write(f"Load Time: {result['load_time']:.2f}s\n")
            f.write("-" * 80 + "\n")

            for test in result["tests"]:
                f.write(f"\nTest: {test['name']}\n")
                f.write(
                    f"Time: {test['generation_time']:.2f}s, "
                    f"Words: {test['word_count']}, "
                    f"Speed: {test['words_per_second']:.1f} w/s\n"
                )
                f.write(f"Response:\n{test['response']}\n")
                f.write("-" * 80 + "\n")

    print(f"\n✅ Results saved to: {output_file}")


if __name__ == "__main__":
    compare_models()
