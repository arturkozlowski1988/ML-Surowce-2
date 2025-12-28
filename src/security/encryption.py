"""
Configuration Encryption Module.
Provides Fernet-based encryption for sensitive configuration data like connection strings.

Uses PBKDF2 key derivation for enhanced security.
OWASP recommendation: 480,000 iterations for PBKDF2-SHA256.
"""

import os
import base64
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger('ConfigEncryption')


class ConfigEncryption:
    """
    Symmetric encryption for configuration data.
    Uses Fernet (AES-128-CBC + HMAC-SHA256).
    
    ⚠️ WARNING: Master key should be stored in HSM/Key Vault in production.
    
    Usage:
        # Encrypt (one-time during setup):
        crypto = ConfigEncryption()
        encrypted = crypto.encrypt("mssql+pyodbc://sa:secret@server/db")
        print(f"ENCRYPTED_DB_CONN_STR={encrypted}")
        
        # Decrypt (at runtime):
        conn_str = crypto.decrypt(os.getenv('ENCRYPTED_DB_CONN_STR'))
    """
    
    # Default salt - should be unique per installation in production
    DEFAULT_SALT = b'AI_Supply_Assistant_v1_2025'
    ITERATIONS = 480000  # OWASP recommendation 2023
    
    def __init__(self, master_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize encryption module.
        
        Args:
            master_key: Master key from env or Key Vault (required)
            salt: Salt for key derivation (unique per installation)
            
        Raises:
            ValueError: If master key is not provided
        """
        load_dotenv()
        
        self.master_key = master_key or os.getenv('ENCRYPTION_MASTER_KEY')
        
        if not self.master_key:
            logger.warning("ENCRYPTION_MASTER_KEY not set - encryption disabled")
            self._fernet = None
            return
        
        self.salt = salt or os.getenv('ENCRYPTION_SALT', '').encode() or self.DEFAULT_SALT
        self._fernet = self._derive_key()
        logger.info("ConfigEncryption initialized")
    
    def _derive_key(self):
        """Derive encryption key from master key using PBKDF2."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=self.ITERATIONS,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
            return Fernet(key)
            
        except ImportError:
            logger.error("cryptography package not installed. Run: pip install cryptography")
            raise ImportError("cryptography package required for encryption")
        except Exception as e:
            logger.error(f"Key derivation failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if encryption is configured and available."""
        return self._fernet is not None
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt text.
        
        Args:
            plaintext: Text to encrypt
            
        Returns:
            Encrypted text (base64 encoded)
            
        Raises:
            RuntimeError: If encryption is not configured
        """
        if not self._fernet:
            raise RuntimeError(
                "Encryption not configured. Set ENCRYPTION_MASTER_KEY in .env"
            )
        
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt text.
        
        Args:
            ciphertext: Encrypted text (base64 encoded)
            
        Returns:
            Decrypted text
            
        Raises:
            RuntimeError: If encryption is not configured
            InvalidToken: If key is wrong or data tampered
        """
        if not self._fernet:
            raise RuntimeError(
                "Encryption not configured. Set ENCRYPTION_MASTER_KEY in .env"
            )
        
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_connection_string(self, conn_str: str) -> dict:
        """
        Encrypt connection string and return with metadata.
        
        Returns:
            Dict with encrypted value and metadata
        """
        return {
            'encrypted': self.encrypt(conn_str),
            'algorithm': 'Fernet (AES-128-CBC + HMAC-SHA256)',
            'kdf': 'PBKDF2-SHA256',
            'iterations': self.ITERATIONS
        }
    
    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new random master key.
        
        Returns:
            Base64-encoded master key suitable for ENCRYPTION_MASTER_KEY
        """
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key().decode()
        except ImportError:
            raise ImportError("cryptography package required")


def get_connection_string(encrypted: bool = True) -> str:
    """
    Get database connection string, decrypting if necessary.
    
    This is a convenience function that:
    1. Checks for ENCRYPTED_DB_CONN_STR first
    2. Falls back to plain DB_CONN_STR if no encrypted version
    
    Args:
        encrypted: Whether to try decryption first
        
    Returns:
        Database connection string (decrypted if was encrypted)
    """
    load_dotenv()
    
    encrypted_conn = os.getenv('ENCRYPTED_DB_CONN_STR')
    
    if encrypted_conn and encrypted:
        try:
            crypto = ConfigEncryption()
            if crypto.is_available():
                return crypto.decrypt(encrypted_conn)
        except Exception as e:
            logger.warning(f"Decryption failed, falling back to plain: {e}")
    
    # Fallback to plain connection string
    plain_conn = os.getenv('DB_CONN_STR')
    if plain_conn:
        return plain_conn
    
    raise ValueError("No database connection string configured")


# CLI for encryption
if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("ConfigEncryption CLI Tool")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python -m src.security.encryption generate-key")
        print("  python -m src.security.encryption encrypt <text>")
        print("  python -m src.security.encryption decrypt <text>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate-key":
        key = ConfigEncryption.generate_master_key()
        print(f"\nGenerated Master Key:")
        print(f"ENCRYPTION_MASTER_KEY={key}")
        print("\nAdd this to your .env file")
        
    elif command == "encrypt":
        if len(sys.argv) < 3:
            print("Error: Missing text to encrypt")
            sys.exit(1)
        
        text = sys.argv[2]
        crypto = ConfigEncryption()
        
        if not crypto.is_available():
            print("Error: ENCRYPTION_MASTER_KEY not set in .env")
            sys.exit(1)
        
        encrypted = crypto.encrypt(text)
        print(f"\nEncrypted value:")
        print(f"{encrypted}")
        
    elif command == "decrypt":
        if len(sys.argv) < 3:
            print("Error: Missing text to decrypt")
            sys.exit(1)
        
        text = sys.argv[2]
        crypto = ConfigEncryption()
        
        if not crypto.is_available():
            print("Error: ENCRYPTION_MASTER_KEY not set in .env")
            sys.exit(1)
        
        decrypted = crypto.decrypt(text)
        print(f"\nDecrypted value:")
        print(f"{decrypted}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
