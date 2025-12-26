import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ai_engine.ollama_client import OllamaClient
import time

def test_model(model_name):
    print(f"\n--- Testing Model: {model_name} ---")
    try:
        client = OllamaClient(model_name=model_name)
        start = time.time()
        # Simple prompt
        response = client.generate_explanation("Say 'Hello' and nothing else.")
        duration = time.time() - start
        
        print(f"Status: Success")
        print(f"Duration: {duration:.2f}s")
        print(f"Response: {response.strip()}")
        return True
    except Exception as e:
        print(f"Status: FAILED")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Verifying Ollama Models...")
    models = ["llama3.2", "ministral-3:8b"]
    results = {}
    for m in models:
        results[m] = test_model(m)
    
    print("\n--- Summary ---")
    for m, res in results.items():
        print(f"{m}: {'OK' if res else 'FAIL'}")
