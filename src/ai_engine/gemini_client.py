import os
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger('GeminiClient')


class GeminiClient:
    """Client for Google Gemini API with retry logic and error handling."""
    
    def __init__(self, api_key: str = None, max_retries: int = 3, retry_delay: float = 1.0):
        load_dotenv()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.model = None
        
        effective_key = api_key or os.getenv('GEMINI_API_KEY')
        if not effective_key:
            logger.warning("GEMINI_API_KEY not found.")
            # We don't raise here strictly to avoid crashing if just checking availability? 
            # But the original code raised ValueError.
            # If we are strictly using this for generation, raising is fine.
            # But if used for check? _check_gemini_configured doesn't instantiate client.
            # So raising is fine.
            raise ValueError("GEMINI_API_KEY is required.")
        
        genai.configure(api_key=effective_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("GeminiClient initialized successfully")

    def generate_explanation(self, prompt: str) -> str:
        """
        Sends prompt to Google Gemini and returns the response.
        Includes retry logic for transient failures.
        """
        if not self.model:
            return "Error: Gemini client not initialized. Check API key."
        
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini API attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff
        
        logger.error(f"Gemini API failed after {self.max_retries} attempts: {last_error}")
        return f"Error calling Gemini API after {self.max_retries} attempts: {last_error}"

