import sys
import os
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ai_engine.ollama_client import OllamaClient

def test_ollama():
    print("Testing Ollama Connection...")
    client = OllamaClient()
    
    # Simple direct check
    try:
        url = client.host
        print(f"Checking {url}...")
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        
        print("Sending test prompt...")
        response = client.generate_explanation("Hello, are you working? Answer with 'Yes'.")
        print(f"Response: {response}")
        
        if "Yes" in response or len(response) > 0:
            print("SUCCESS: Ollama is responding.")
        else:
            print("WARNING: Response empty or unexpected.")
            
    except Exception as e:
        print(f"FAILURE: {e}")
        print("Ensure 'ollama serve' is running in another terminal.")

if __name__ == "__main__":
    test_ollama()
