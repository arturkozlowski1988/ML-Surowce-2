"""
Configuration models with Pydantic validation.
Ensures all sensitive data comes from environment variables.
"""

import os
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

logger = logging.getLogger('Config')


class DatabaseConfig(BaseModel):
    """Validated database configuration."""
    server: str = Field(..., min_length=1, description="SQL Server hostname/instance")
    database: str = Field(..., min_length=1, description="Database name")
    user: str = Field(..., min_length=1, description="Database username")
    password: str = Field(..., min_length=1, description="Database password")
    driver: str = Field(default="ODBC Driver 17 for SQL Server")
    trust_cert: bool = Field(default=True)
    
    @field_validator('server', 'database', 'user')
    @classmethod
    def not_placeholder(cls, v: str, info) -> str:
        """Ensure values are not placeholders."""
        placeholders = ['YOUR_SERVER', 'YOUR_DATABASE', 'YOUR_USER', 'YOUR_PASSWORD', '']
        if v.upper() in [p.upper() for p in placeholders]:
            raise ValueError(f"{info.field_name} cannot be a placeholder value")
        return v
    
    def get_connection_string(self) -> str:
        """Builds SQLAlchemy connection string."""
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.password)
        return (
            f"mssql+pyodbc://{self.user}:{encoded_password}@{self.server}/{self.database}"
            f"?driver={self.driver.replace(' ', '+')}&TrustServerCertificate={'yes' if self.trust_cert else 'no'}"
        )


class AIConfig(BaseModel):
    """AI service configuration."""
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server URL")
    
    @field_validator('gemini_api_key')
    @classmethod
    def validate_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Gemini API key format if provided."""
        if v and not v.startswith('AIza'):
            logger.warning("Gemini API key may be invalid (expected prefix 'AIza')")
        return v


class AppConfig(BaseModel):
    """Main application configuration."""
    database: Optional[DatabaseConfig] = None
    ai: AIConfig = Field(default_factory=AIConfig)
    debug: bool = Field(default=False)


def parse_connection_string(conn_str: str) -> dict:
    """
    Parses SQLAlchemy connection string into components.
    Format: mssql+pyodbc://user:password@server/database?params
    """
    import urllib.parse
    from urllib.parse import urlparse, parse_qs
    
    try:
        # Handle mssql+pyodbc:// prefix
        if conn_str.startswith('mssql+pyodbc://'):
            conn_str = conn_str.replace('mssql+pyodbc://', 'http://')
        
        parsed = urlparse(conn_str)
        query_params = parse_qs(parsed.query)
        
        return {
            'user': urllib.parse.unquote(parsed.username or ''),
            'password': urllib.parse.unquote(parsed.password or ''),
            'server': parsed.hostname or '',
            'database': parsed.path.lstrip('/'),
            'driver': query_params.get('driver', ['ODBC Driver 17 for SQL Server'])[0].replace('+', ' '),
            'trust_cert': query_params.get('TrustServerCertificate', ['yes'])[0].lower() == 'yes'
        }
    except Exception as e:
        logger.error(f"Failed to parse connection string: {e}")
        raise ValueError(f"Invalid connection string format: {e}")


def get_validated_config() -> AppConfig:
    """
    Loads and validates configuration from environment variables.
    Raises ValueError if required configuration is missing or invalid.
    """
    load_dotenv()
    
    config = AppConfig()
    
    # Parse database config from connection string
    conn_str = os.getenv('DB_CONN_STR')
    if conn_str:
        try:
            db_parts = parse_connection_string(conn_str)
            config.database = DatabaseConfig(**db_parts)
            logger.info("Database configuration loaded and validated")
        except Exception as e:
            logger.error(f"Database configuration error: {e}")
            raise ValueError(f"Invalid database configuration: {e}")
    else:
        logger.warning("DB_CONN_STR not found in environment")
    
    # Load AI config
    config.ai = AIConfig(
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        ollama_host=os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    )
    
    config.debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    return config


def get_safe_display_config(config: AppConfig) -> dict:
    """Returns config dict with masked sensitive values for display."""
    result = {
        'database': None,
        'ai': {
            'gemini_configured': config.ai.gemini_api_key is not None,
            'ollama_host': config.ai.ollama_host
        },
        'debug': config.debug
    }
    
    if config.database:
        result['database'] = {
            'server': config.database.server,
            'database': config.database.database,
            'user': config.database.user,
            'password': '***MASKED***'
        }
    
    return result
