"""
Secrets Manager - Enterprise-grade secrets handling.
Provides abstraction layer for secrets with support for multiple backends:
- Environment variables / .env files (development)
- Azure Key Vault (production - optional)

This module eliminates hardcoded credentials and enables secure deployment.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict
from dotenv import load_dotenv

logger = logging.getLogger('SecretsManager')


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieves a secret by key."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available."""
        pass


class EnvFileBackend(SecretsBackend):
    """
    Backend for .env files and environment variables.
    Default backend for development environments.
    """
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        self._loaded = False
        self._load()
    
    def _load(self):
        """Load environment variables from .env file."""
        if os.path.exists(self.env_path):
            load_dotenv(self.env_path)
            self._loaded = True
            logger.debug(f"Loaded secrets from {self.env_path}")
        else:
            logger.warning(f"No .env file found at {self.env_path}")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from environment variables."""
        return os.getenv(key)
    
    def is_available(self) -> bool:
        """Environment backend is always available."""
        return True


class AzureKeyVaultBackend(SecretsBackend):
    """
    Backend for Azure Key Vault.
    Used for production deployments with enterprise security requirements.
    
    Requires:
        pip install azure-keyvault-secrets azure-identity
        
    Environment variables:
        AZURE_KEYVAULT_URL: The Key Vault URL (e.g., https://myvault.vault.azure.net/)
    """
    
    def __init__(self, vault_url: Optional[str] = None):
        self.vault_url = vault_url or os.getenv('AZURE_KEYVAULT_URL')
        self.client = None
        self._available = False
        
        if self.vault_url:
            self._initialize()
    
    def _initialize(self):
        """Initialize Azure Key Vault client."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)
            self._available = True
            logger.info(f"Connected to Azure Key Vault: {self.vault_url}")
            
        except ImportError:
            logger.debug("Azure SDK not installed - Key Vault backend unavailable")
            logger.debug("To enable: pip install azure-keyvault-secrets azure-identity")
        except Exception as e:
            logger.warning(f"Failed to connect to Azure Key Vault: {e}")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from Azure Key Vault."""
        if not self._available or not self.client:
            return None
        
        try:
            # Azure Key Vault uses dashes instead of underscores
            azure_key = key.replace('_', '-')
            secret = self.client.get_secret(azure_key)
            return secret.value
        except Exception as e:
            logger.debug(f"Secret '{key}' not found in Azure Key Vault: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if Azure Key Vault client is initialized."""
        return self._available


class SecretsManager:
    """
    Centralized secrets management with multi-backend support.
    
    Priority order:
    1. Azure Key Vault (if configured)
    2. Environment variables / .env file
    
    Usage:
        secrets = SecretsManager()
        db_conn_str = secrets.get('DB_CONN_STR')
        api_key = secrets.get('GEMINI_API_KEY', required=False)
    """
    
    _instance: Optional['SecretsManager'] = None
    
    def __new__(cls):
        """Singleton pattern - only one instance per application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.backends: list = []
        self._cache: Dict[str, str] = {}
        self._setup_backends()
        self._initialized = True
        logger.info(f"SecretsManager initialized with {len(self.backends)} backend(s)")
    
    def _setup_backends(self):
        """Configure available backends in priority order."""
        
        # 1. Try Azure Key Vault (production)
        azure_backend = AzureKeyVaultBackend()
        if azure_backend.is_available():
            self.backends.append(azure_backend)
            logger.info("Azure Key Vault backend enabled")
        
        # 2. Environment variables / .env (always as fallback)
        env_backend = EnvFileBackend()
        self.backends.append(env_backend)
        logger.info("Environment variables backend enabled")
    
    def get(self, key: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from the first available backend.
        
        Args:
            key: Secret name (e.g., 'DB_CONN_STR', 'GEMINI_API_KEY')
            required: If True, raises ValueError when secret not found
            default: Default value if secret not found and not required
            
        Returns:
            Secret value or default
            
        Raises:
            ValueError: If required=True and secret not found
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Try each backend in order
        for backend in self.backends:
            try:
                value = backend.get_secret(key)
                if value is not None:
                    self._cache[key] = value
                    logger.debug(f"Secret '{key}' retrieved from {type(backend).__name__}")
                    return value
            except Exception as e:
                logger.warning(f"Backend {type(backend).__name__} failed for '{key}': {e}")
                continue
        
        # Secret not found
        if required:
            raise ValueError(
                f"Required secret '{key}' not found in any backend. "
                f"Please set it in .env file or Azure Key Vault."
            )
        
        return default
    
    def get_masked(self, key: str, mask_char: str = '*', visible_chars: int = 4) -> str:
        """
        Get secret value with masking for display purposes.
        
        Args:
            key: Secret name
            mask_char: Character to use for masking
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked secret string (e.g., "********Y20")
        """
        try:
            value = self.get(key, required=False)
            if not value:
                return "[NOT SET]"
            
            if len(value) <= visible_chars:
                return mask_char * len(value)
            
            return mask_char * (len(value) - visible_chars) + value[-visible_chars:]
        except Exception:
            return "[ERROR]"
    
    def clear_cache(self):
        """Clear the secrets cache (e.g., before key rotation)."""
        self._cache.clear()
        logger.info("Secrets cache cleared")
    
    def get_status(self) -> Dict[str, str]:
        """
        Get status of all configured backends.
        
        Returns:
            Dict with backend names and their status
        """
        status = {}
        for backend in self.backends:
            name = type(backend).__name__
            status[name] = "available" if backend.is_available() else "unavailable"
        return status
    
    def list_required_secrets(self) -> list:
        """
        List all secrets that should be configured.
        
        Returns:
            List of required secret names
        """
        return [
            'DB_CONN_STR',
            'GEMINI_API_KEY',
            'OLLAMA_HOST',
            'LOCAL_LLM_PATH'
        ]
    
    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate that all required secrets are configured.
        
        Returns:
            Dict with secret names and their configuration status
        """
        result = {}
        for key in self.list_required_secrets():
            try:
                value = self.get(key, required=False)
                result[key] = value is not None and len(value) > 0
            except Exception:
                result[key] = False
        return result


# Convenience function for quick access
def get_secret(key: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    """
    Quick access to secrets without explicit SecretsManager instantiation.
    
    Usage:
        from src.security.secrets_manager import get_secret
        db_conn = get_secret('DB_CONN_STR')
    """
    return SecretsManager().get(key, required=required, default=default)
