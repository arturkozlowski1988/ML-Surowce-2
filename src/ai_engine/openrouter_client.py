"""
OpenRouter AI Client - Access to 100+ AI models through one API.

OpenRouter provides unified access to models from:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini, PaLM)
- Meta (Llama)
- Mistral
- And many more free/paid models

API is OpenAI-compatible, so we use the openai library.
"""

import os
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger('OpenRouterClient')


@dataclass
class OpenRouterModel:
    """Information about an OpenRouter model."""
    id: str  # Full model ID for API
    name: str  # Display name
    provider: str  # Provider name (OpenAI, Anthropic, etc.)
    context_length: int  # Max tokens
    is_free: bool  # Free tier available
    description: str  # Model description
    
    @property
    def display_name(self) -> str:
        free_badge = "🆓 " if self.is_free else "💰 "
        return f"{free_badge}{self.name} ({self.provider})"


# Popular models available on OpenRouter
# Updated: January 2026
OPENROUTER_MODELS: List[OpenRouterModel] = [
    # Free models
    OpenRouterModel(
        id="meta-llama/llama-3.2-3b-instruct:free",
        name="Llama 3.2 3B Instruct",
        provider="Meta",
        context_length=131072,
        is_free=True,
        description="Szybki, darmowy model Meta. Dobry do prostych zadań."
    ),
    OpenRouterModel(
        id="meta-llama/llama-3.1-8b-instruct:free",
        name="Llama 3.1 8B Instruct",
        provider="Meta",
        context_length=131072,
        is_free=True,
        description="Większy darmowy model Llama. Lepsza jakość."
    ),
    OpenRouterModel(
        id="google/gemma-2-9b-it:free",
        name="Gemma 2 9B",
        provider="Google",
        context_length=8192,
        is_free=True,
        description="Darmowy model Google. Dobra jakość."
    ),
    OpenRouterModel(
        id="mistralai/mistral-7b-instruct:free",
        name="Mistral 7B Instruct",
        provider="Mistral",
        context_length=32768,
        is_free=True,
        description="Darmowy model Mistral. Szybki i wydajny."
    ),
    OpenRouterModel(
        id="qwen/qwen-2.5-7b-instruct:free",
        name="Qwen 2.5 7B Instruct",
        provider="Qwen",
        context_length=32768,
        is_free=True,
        description="Darmowy model Qwen. Dobra obsługa wielu języków."
    ),
    OpenRouterModel(
        id="microsoft/phi-3-mini-128k-instruct:free",
        name="Phi-3 Mini 128K",
        provider="Microsoft",
        context_length=128000,
        is_free=True,
        description="Mały ale wydajny model Microsoft. Długi kontekst."
    ),
    
    # Paid models (popular)
    OpenRouterModel(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        context_length=128000,
        is_free=False,
        description="Najnowszy ekonomiczny model OpenAI. Świetna jakość."
    ),
    OpenRouterModel(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        context_length=128000,
        is_free=False,
        description="Flagowy model OpenAI. Najwyższa jakość."
    ),
    OpenRouterModel(
        id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="Anthropic",
        context_length=200000,
        is_free=False,
        description="Najlepszy model Anthropic. Doskonały do analizy."
    ),
    OpenRouterModel(
        id="anthropic/claude-3-haiku",
        name="Claude 3 Haiku",
        provider="Anthropic",
        context_length=200000,
        is_free=False,
        description="Szybki i tani model Claude. Dobry kompromis."
    ),
    OpenRouterModel(
        id="google/gemini-2.0-flash-001",
        name="Gemini 2.0 Flash",
        provider="Google",
        context_length=1000000,
        is_free=False,
        description="Najnowszy Gemini. Bardzo długi kontekst."
    ),
    OpenRouterModel(
        id="mistralai/mistral-large-2411",
        name="Mistral Large",
        provider="Mistral",
        context_length=128000,
        is_free=False,
        description="Największy model Mistral. Wysoka jakość."
    ),
    OpenRouterModel(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B Instruct",
        provider="Meta",
        context_length=131072,
        is_free=False,
        description="Największy Llama. Bardzo dobra jakość."
    ),
    OpenRouterModel(
        id="deepseek/deepseek-chat",
        name="DeepSeek Chat V3",
        provider="DeepSeek",
        context_length=64000,
        is_free=False,
        description="Model DeepSeek. Bardzo tani i dobry."
    ),
]


class OpenRouterClient:
    """
    Client for OpenRouter API - unified access to 100+ AI models.
    
    Usage:
        client = OpenRouterClient()
        response = client.generate_explanation("Analyze this data...")
        
        # With specific model
        client = OpenRouterClient(model_id="anthropic/claude-3.5-sonnet")
    """
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(
        self, 
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        load_dotenv()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = None
        self.model_id = model_id or "meta-llama/llama-3.2-3b-instruct:free"
        
        # Priority: explicit arg > env var
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not found.")
            # Don't raise error immediately if just checking status, 
            # but usually we want to fail fast if trying to use it.
            # We'll allow instantiation but methods might fail.
            pass
        
        # Use OpenAI client with OpenRouter base URL
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    base_url=self.BASE_URL,
                    api_key=self.api_key,
                    default_headers={
                        "HTTP-Referer": "https://ai-supply-assistant.local",
                        "X-Title": "AI Supply Assistant"
                    }
                )
                logger.info(f"OpenRouterClient initialized with model: {self.model_id}")
            except ImportError:
                logger.error("openai library not found.")
                self.client = None
        else:
            logger.warning("Client not initialized (no API key).")
    
    def set_model(self, model_id: str):
        """Change the active model."""
        self.model_id = model_id
        logger.info(f"OpenRouter model changed to: {model_id}")
    
    def generate_explanation(self, prompt: str) -> str:
        """
        Sends prompt to OpenRouter and returns the response.
        Includes retry logic for transient failures.
        """
        if not self.client:
            return "Error: OpenRouter client not initialized. Check API key."
        
        import time
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4096,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
            except Exception as e:
                last_error = e
                logger.warning(f"OpenRouter API attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
        
        logger.error(f"OpenRouter API failed after {self.max_retries} attempts: {last_error}")
        return f"Error calling OpenRouter API: {last_error}"
    
    @staticmethod
    def fetch_models_from_api() -> List[OpenRouterModel]:
        """
        Fetches available models from OpenRouter API dynamically.
        Filters out image generation models.
        """
        import requests
        
        try:
            response = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch models: {response.status_code}")
                return OPENROUTER_MODELS
            
            data = response.json()
            models_data = data.get('data', [])
            
            models = []
            
            # Keywords to filter out (image generation, etc.)
            excluded_keywords = ['diffusion', 'diffusers', 'flux', 'midjourney', 'dall-e', 'stable-diffusion', 'tts', 'audio']
            
            for m in models_data:
                mid = m.get('id', '')
                arch = m.get('architecture', {})
                
                # Filter by modality if available (prefer text->text)
                if isinstance(arch, dict):
                    modality = arch.get('modality', '')
                    # If modality is explicit and not text->text, skip
                    if modality and 'text->text' not in modality:
                        continue
                
                # Filter by ID keywords
                if any(kw in mid.lower() for kw in excluded_keywords):
                    continue
                
                # Determine provider from ID prefix or name
                provider = "OpenRouter"
                if '/' in mid:
                    provider = mid.split('/')[0].title()
                
                # Pricing check (rough approximation based on ID convention or missing field)
                # Ideally we check 'pricing' object: {'prompt': '...', 'completion': '...'}
                pricing = m.get('pricing', {})
                is_free = False
                if pricing:
                    prompt_price = float(pricing.get('prompt', 0))
                    completion_price = float(pricing.get('completion', 0))
                    if prompt_price == 0 and completion_price == 0:
                        is_free = True
                elif ":free" in mid:
                    is_free = True
                
                models.append(OpenRouterModel(
                    id=mid,
                    name=m.get('name', mid),
                    provider=provider,
                    context_length=int(m.get('context_length', 4096)),
                    is_free=is_free,
                    description=m.get('description', '')
                ))
            
            # Sort: Free models first, then by name
            models.sort(key=lambda x: (not x.is_free, x.name))
            
            logger.info(f"Fetched {len(models)} models from OpenRouter API")
            return models
            
        except Exception as e:
            logger.error(f"Error fetching OpenRouter models: {e}")
            return OPENROUTER_MODELS

    @staticmethod
    def get_available_models(free_only: bool = False, force_refresh: bool = False) -> List[OpenRouterModel]:
        """Get list of available models, optionally fetching fresh list."""
        if force_refresh:
            models = OpenRouterClient.fetch_models_from_api()
        else:
            # First try to use static list for speed, or fetch if needed
            # For now, let's default to static unless refreshed, 
            # BUT the user wants dynamic. So let's make it fetch if user asks.
            # Actually, let's keep OPENROUTER_MODELS as fallback, but expose fetch.
            # We can cache the result in a class variable.
             models = OPENROUTER_MODELS
        
        if free_only:
            return [m for m in models if m.is_free]
        return models
    
    @staticmethod
    def get_model_by_id(model_id: str) -> Optional[OpenRouterModel]:
        """Get model info by ID."""
        # Check static list first
        for model in OPENROUTER_MODELS:
            if model.id == model_id:
                return model
        # If not found, maybe fetch? (Skipping for now to avoid latency on every lookup)
        return None


def test_openrouter():
    """Test OpenRouter connection."""
    try:
        client = OpenRouterClient()
        response = client.generate_explanation("Say 'Hello from OpenRouter!' in Polish.")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    test_openrouter()
