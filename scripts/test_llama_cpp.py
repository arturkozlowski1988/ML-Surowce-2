"""
Test llama-cpp installation and model loading with verbose output.
"""

import sys
from pathlib import Path

try:
    from llama_cpp import Llama
    print("✅ llama-cpp-python imported successfully")
    print(f"Version info: {Llama.__module__}")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

model_path = "models/deepseek-r1-14b-q4_k_m.gguf"

if not Path(model_path).exists():
    print(f"❌ Model not found: {model_path}")
    sys.exit(1)

print(f"\n✅ Model file exists: {model_path}")
print(f"Size: {Path(model_path).stat().st_size / (1024**3):.2f} GB")

print("\n⏳ Loading model with verbose=True...")
print("-" * 80)

try:
    llm = Llama(
        model_path=model_path,
        n_ctx=512,  # Small context for testing
        n_threads=4,
        verbose=True
    )
    print("-" * 80)
    print("\n✅ Model loaded successfully!")
    
    # Test generation
    print("\n🧪 Testing generation...")
    output = llm("Test: Supply chain", max_tokens=20, temperature=0.7)
    print(f"Response: {output['choices'][0]['text']}")
    
except Exception as e:
    print("-" * 80)
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
