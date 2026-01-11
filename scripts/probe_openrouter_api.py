
import requests
import json

def check_openrouter_models():
    url = "https://openrouter.ai/api/v1/models"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        models = data.get('data', [])
        print(f"Found {len(models)} models.")
        
        # Print first 3 models to see structure
        if models:
            m = models[0]
            print(f"Keys: {list(m.keys())}")
            print(f"ID: {m.get('id')}")
            print(f"Name: {m.get('name')}")
            print(f"Context: {m.get('context_length')}")
            print(f"Pricing: {m.get('pricing')}")
            print(f"Architecture: {m.get('architecture')}")
            
            # Check for modality or tags to filter images
            print("Checking tags/architecture for first 5 models:")
            for item in models[:5]:
                 print(f" - {item.get('id')} | Arch: {item.get('architecture')} | Desc: {item.get('description')[:50]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_openrouter_models()
