import os
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger('GeminiClient')


class GeminiClient:
    """Client for Google Gemini API with retry logic and error handling."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        load_dotenv()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.model = None
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables.")
            raise ValueError("GEMINI_API_KEY is required. Please set it in your .env file.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
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

