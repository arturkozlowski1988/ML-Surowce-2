"""
Local LLM Engine using llama-cpp-python.
Provides embedded LLM inference without external dependencies like Ollama.

This module enables portable deployment by bundling the model directly
with the application, eliminating the need for external LLM servers.
"""

import os
import logging
import multiprocessing
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger('LocalLLMEngine')


class LocalLLMEngine:
    """
    Embedded LLM engine using llama-cpp-python.
    Supports GGUF model format with automatic CPU/GPU detection.
    
    Usage:
        engine = LocalLLMEngine(model_path="models/phi-3-mini-4k-instruct.Q4_K_M.gguf")
        response = engine.generate("Explain supply chain optimization")
    """
    
    # Recommended models for low-resource environments
    RECOMMENDED_MODELS = {
        'qwen2.5-3b': {
            'name': 'Qwen2.5 3B Instruct',
            'file': 'qwen2.5-3b-instruct-q4_k_m.gguf',
            'url': 'https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf',
            'size_gb': 1.96,
            'context': 32768,
            'description': 'Fast and efficient - Latest Dec 2024, excellent for business analysis'
        },
        'qwen2.5-7b': {
            'name': 'Qwen2.5 7B Instruct',
            'file': 'qwen2.5-7b-instruct-q3_k_m.gguf',
            'url': 'https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q3_k_m.gguf',
            'size_gb': 3.81,
            'context': 32768,
            'description': 'Balanced - Best quality/speed ratio for supply chain analysis'
        },
        'deepseek-r1-14b': {
            'name': 'DeepSeek-R1 14B',
            'file': 'deepseek-r1-14b-q4_k_m.gguf',
            'url': 'https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf',
            'size_gb': 8.0,
            'context': 32768,
            'description': 'Advanced reasoning - DeepSeek R1 distilled model for complex analysis'
        },
        'mistral-small-24b': {
            'name': 'Mistral-Small 24B',
            'file': 'mistral-small-24b-q4_k_m.gguf',
            'url': 'https://huggingface.co/bartowski/Mistral-Small-Instruct-2409-GGUF/resolve/main/Mistral-Small-Instruct-2409-Q4_K_M.gguf',
            'size_gb': 14.0,
            'context': 32768,
            'description': 'Most powerful - Best quality for critical business decisions'
        },
        'phi-3-mini': {
            'name': 'Phi-3 Mini 4K Instruct',
            'file': 'Phi-3-mini-4k-instruct-q4.gguf',
            'url': 'https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf',
            'size_gb': 2.2,
            'context': 4096,
            'description': 'Legacy - Fast, efficient model for general tasks'
        },
        'qwen2-1.5b': {
            'name': 'Qwen2 1.5B Instruct',
            'file': 'qwen2-1_5b-instruct-q4_k_m.gguf',
            'url': 'https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_k_m.gguf',
            'size_gb': 1.1,
            'context': 8192,
            'description': 'Legacy - Smallest recommended model, very fast'
        }
    }
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        n_ctx: int = 2048,
        n_threads: Optional[int] = None,
        verbose: bool = False
    ):
        """
        Initialize the Local LLM Engine.
        
        Args:
            model_path: Path to GGUF model file. If None, uses env var LOCAL_LLM_PATH
            n_ctx: Context window size (default: 2048)
            n_threads: Number of CPU threads (default: auto-detect)
            verbose: Enable verbose logging from llama.cpp
        """
        load_dotenv()
        
        self.model_path = model_path or os.getenv('LOCAL_LLM_PATH')
        self.n_ctx = n_ctx
        self.verbose = verbose
        self.llm = None
        self._is_initialized = False
        self._init_error = None
        
        # Auto-detect optimal thread count
        if n_threads is None:
            cpu_count = multiprocessing.cpu_count()
            # Use n-2 threads to leave room for system, minimum 1
            self.n_threads = max(1, cpu_count - 2)
        else:
            self.n_threads = n_threads
        
        logger.info(f"LocalLLMEngine configured with {self.n_threads} threads")
    
    def _initialize(self) -> bool:
        """
        Lazily initialize the LLM model.
        Returns True if successful, False otherwise.
        """
        if self._is_initialized:
            return True
        
        if not self.model_path:
            self._init_error = "No model path configured. Set LOCAL_LLM_PATH in .env"
            logger.error(self._init_error)
            return False
        
        model_file = Path(self.model_path)
        if not model_file.exists():
            self._init_error = f"Model file not found: {self.model_path}"
            logger.error(self._init_error)
            return False
        
        try:
            from llama_cpp import Llama
            
            logger.info(f"Loading model from: {self.model_path}")
            logger.info(f"Context size: {self.n_ctx}, Threads: {self.n_threads}")
            
            self.llm = Llama(
                model_path=str(model_file),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=self.verbose
            )
            
            self._is_initialized = True
            logger.info("LocalLLMEngine initialized successfully")
            return True
            
        except ImportError:
            self._init_error = "llama-cpp-python not installed. Run: pip install llama-cpp-python"
            logger.error(self._init_error)
            return False
        except Exception as e:
            self._init_error = f"Failed to load model: {str(e)}"
            logger.error(self._init_error)
            return False
    
    def is_available(self) -> bool:
        """Check if the LLM is ready for inference."""
        return self._is_initialized and self.llm is not None
    
    def get_status(self) -> dict:
        """Get engine status information."""
        return {
            'initialized': self._is_initialized,
            'model_path': self.model_path,
            'n_threads': self.n_threads,
            'n_ctx': self.n_ctx,
            'error': self._init_error
        }
    
    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: List of stop sequences
            
        Returns:
            Generated text string
        """
        if not self._initialize():
            return f"Error: {self._init_error}"
        
        if stop is None:
            stop = ["\n\n", "User:", "Human:"]
        
        try:
            output = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                echo=False
            )
            
            if output and 'choices' in output and output['choices']:
                return output['choices'][0]['text'].strip()
            else:
                return "Error: Empty response from model"
                
        except Exception as e:
            error_msg = f"Generation error: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def generate_explanation(self, prompt: str) -> str:
        """
        Generate explanation (compatible interface with OllamaClient/GeminiClient).
        
        Args:
            prompt: The prompt to process
            
        Returns:
            Generated explanation text
        """
        # Format prompt similar to Gemini/Ollama for consistent response style
        # Using Qwen2.5 chat template format
        formatted_prompt = f"""<|im_start|>system
Jesteś ekspertem ds. łańcucha dostaw i zakupów w firmie produkcyjnej.

ZASADY ODPOWIEDZI:
1. Odpowiadaj ZAWSZE w języku polskim
2. Używaj struktury z nagłówkami i punktami (•)
3. Bądź konkretny i praktyczny
4. Podawaj rekomendacje dla działu zakupów
5. Format odpowiedzi:
   - Krótkie podsumowanie trendu
   - Przyczyny anomalii (lista punktowana)
   - Rekomendacja działania
<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
"""
        
        return self.generate(
            formatted_prompt, 
            max_tokens=1024,  # More tokens for detailed response
            temperature=0.7,
            stop=["<|im_end|>", "<|im_start|>", "User:", "Human:"]
        )


def check_local_llm_available() -> tuple:
    """
    Check if Local LLM is configured and available.
    
    Returns:
        Tuple of (is_available: bool, message: str)
    """
    load_dotenv()
    
    model_path = os.getenv('LOCAL_LLM_PATH')
    
    if not model_path:
        return False, "LOCAL_LLM_PATH not configured in .env"
    
    if not Path(model_path).exists():
        return False, f"Model file not found: {model_path}"
    
    try:
        from llama_cpp import Llama
        return True, f"Ready: {Path(model_path).name}"
    except ImportError:
        return False, "llama-cpp-python not installed"


def get_recommended_models() -> dict:
    """Get dictionary of recommended models for download."""
    return LocalLLMEngine.RECOMMENDED_MODELS
