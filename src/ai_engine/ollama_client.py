import os

import requests
from dotenv import load_dotenv


class OllamaClient:
    def __init__(self, host=None, model_name="llama3.1"):
        load_dotenv()
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model_name = model_name

    def generate_explanation(self, prompt: str) -> str:
        """
        Generates explanation using Ollama.
        """
        url = f"{self.host}/api/generate"
        payload = {"model": self.model_name, "prompt": prompt, "stream": False}

        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error: Ollama returned status {response.status_code}"
        except Exception as e:
            return f"Error connecting to Ollama: {e}. Ensure 'ollama serve' is running."
