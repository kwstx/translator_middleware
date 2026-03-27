from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import os

class CryptoService:
    _fernet: Fernet = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet is None:
            key = settings.PROVIDER_CREDENTIALS_ENCRYPTION_KEY
            if not key:
                # In development, we might want a fallback, but for production it's a security risk.
                # We'll use the AUTH_JWT_SECRET as a base to derive a key if not provided,
                # but better to raise an error if it's not set in production.
                if settings.ENVIRONMENT == "production":
                    raise ValueError("PROVIDER_CREDENTIALS_ENCRYPTION_KEY must be set in production")
                
                # Derive a key from AUTH_JWT_SECRET if available
                if settings.AUTH_JWT_SECRET:
                    # Fernet key must be 32 url-safe base64-encoded bytes
                    # We'll just pad/truncate the secret for a deterministic dev key
                    raw_key = settings.AUTH_JWT_SECRET.encode().ljust(32, b"0")[:32]
                    key = base64.urlsafe_b64encode(raw_key).decode()
                else:
                    # Fallback to a random key for the session (volatile!)
                    key = Fernet.generate_key().decode()
            
            cls._fernet = Fernet(key.encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        if not plain_text:
            return ""
        fernet = cls._get_fernet()
        return fernet.encrypt(plain_text.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        fernet = cls._get_fernet()
        try:
            return fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # Handle decryption failure (e.g., wrong key)
            return ""
