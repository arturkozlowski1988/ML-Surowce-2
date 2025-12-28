"""
Quick test for DeepSeek-R1 14B model.
Tests basic functionality before full comparison.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_engine.local_llm import LocalLLMEngine

def test_deepseek():
    """Quick test of DeepSeek-R1 model."""
    
    model_path = "models/deepseek-r1-14b-q4_k_m.gguf"
    
    print("="*80)
    print("DeepSeek-R1 14B - Quick Test")
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
    
    # Test prompt
    test_prompt = """Przeanalizuj następujący trend zużycia surowca:

Surowiec: STAL 316L
Trend: Wzrost o 35% w ostatnich 3 miesiącach
Średnie zużycie: 2500 kg/miesiąc
Obecne zużycie: 3375 kg/miesiąc
Dni do wyczerpania zapasu: 12 dni

Podaj krótką analizę i rekomendację dla działu zakupów."""
    
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
    
    print("\n✅ DeepSeek-R1 test completed successfully!")
    print("\n💡 Next step: Run full comparison with:")
    print("   python scripts/compare_models.py")

if __name__ == "__main__":
    test_deepseek()
