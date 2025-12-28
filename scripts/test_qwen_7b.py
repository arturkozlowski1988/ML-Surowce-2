"""
Quick test for Qwen2.5-7B model.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_engine.local_llm import LocalLLMEngine

def test_qwen_7b():
    """Quick test of Qwen2.5-7B model."""
    
    model_path = "models/qwen2.5-7b-instruct-q4_k_m.gguf"
    
    print("="*80)
    print("Qwen2.5-7B Instruct - Quick Test")
    print("="*80)
    
    if not Path(model_path).exists():
        print(f"❌ Model not found: {model_path}")
        return
    
    print(f"\n✅ Model file found: {model_path}")
    print(f"Size: {Path(model_path).stat().st_size / (1024**3):.2f} GB")
    
    print("\n⏳ Loading model (this may take 30-60 seconds)...")
    
    engine = LocalLLMEngine(
        model_path=model_path,
        n_ctx=4096,
        verbose=False
    )
    
    # Test prompt - Supply chain analysis
    test_prompt = """Przeanalizuj następujący trend zużycia surowca:

Surowiec: STAL 316L
Trend: Wzrost o 35% w ostatnich 3 miesiącach
Średnie zużycie: 2500 kg/miesiąc
Obecne zużycie: 3375 kg/miesiąc
Dni do wyczerpania zapasu: 12 dni

Podaj analizę i rekomendację dla działu zakupów."""
    
    print("\n📝 Test prompt:")
    print("-" * 80)
    print(test_prompt)
    print("-" * 80)
    
    print("\n🤖 Generating response...")
    response = engine.generate_explanation(test_prompt)
    
    print("\n💡 Response:")
    print("="*80)
    print(response)
    print("="*80)
    
    # Stats
    words = len(response.split())
    print(f"\n📊 Response stats:")
    print(f"   Words: {words}")
    print(f"   Characters: {len(response)}")
    
    print("\n✅ Qwen2.5-7B test completed successfully!")
    print("\n💡 Model comparison:")
    print("   - Qwen2.5-3B: Fast & efficient")
    print("   - Qwen2.5-7B: Better quality (current test)")
    print("   - Mistral-Small-24B: Premium quality (downloading...)")

if __name__ == "__main__":
    test_qwen_7b()
