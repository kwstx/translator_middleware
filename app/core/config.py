from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Translator Middleware"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    HTTPS_ONLY: bool = False
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_ENABLED: bool = True
    
    # Postgres
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "translator_db"

    # Redis
    REDIS_ENABLED: bool = True
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None
    REDIS_CONNECT_TIMEOUT_SECONDS: float = 0.2
    REDIS_SOCKET_TIMEOUT_SECONDS: float = 0.2
    SEMANTIC_CACHE_TTL_SECONDS: int = 600

    # ML mapping suggestions
    ML_ENABLED: bool = True
    ML_MODEL_PATH: str = "app/semantic/models/mapping_model.joblib"
    ML_MIN_TRAIN_SAMPLES: int = 20
    ML_AUTO_APPLY_THRESHOLD: float = 0.85
    MAPPING_FAILURE_MAX_FIELDS: int = 50
    MAPPING_FAILURE_PAYLOAD_MAX_KEYS: int = 50
    
    DATABASE_URL: Optional[str] = None

    # Task queue (SQL-backed)
    TASK_POLL_INTERVAL_SECONDS: float = 2.0
    TASK_LEASE_SECONDS: int = 60
    TASK_MAX_ATTEMPTS: int = 5
    AGENT_MESSAGE_LEASE_SECONDS: int = 60
    AGENT_MESSAGE_MAX_ATTEMPTS: int = 5

    # Auth
    AUTH_ISSUER: str = "https://auth.example.com/"
    AUTH_AUDIENCE: str = "translator-middleware"
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_JWT_SECRET: Optional[str] = None
    AUTH_JWT_PUBLIC_KEY: Optional[str] = None

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _finalize_database_url(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )
        elif self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = "postgresql+asyncpg://" + self.DATABASE_URL[len("postgres://") :]
        elif (
            self.DATABASE_URL.startswith("postgresql://")
            and "+asyncpg" not in self.DATABASE_URL
        ):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )

        # asyncpg does not accept sslmode=*, so map it to ssl=true/false.
        if self.DATABASE_URL and "+asyncpg" in self.DATABASE_URL:
            parts = urlsplit(self.DATABASE_URL)
            raw_pairs = parse_qsl(parts.query, keep_blank_values=True)
            cleaned_pairs = []
            sslmode_value = None
            for key, value in raw_pairs:
                key_clean = key.strip().lower()
                value_clean = value.strip().strip("\"'")
                if key_clean == "sslmode":
                    sslmode_value = value_clean
                    continue
                if key_clean in {"channel_binding", "sslrootcert", "sslcert", "sslkey", "sslcrl"}:
                    continue
                cleaned_pairs.append((key.strip(), value_clean))

            if sslmode_value and not any(k.strip().lower() == "ssl" for k, _ in cleaned_pairs):
                if sslmode_value in {"require", "verify-full", "verify-ca"}:
                    cleaned_pairs.append(("ssl", "true"))
                elif sslmode_value in {"disable", "allow", "prefer"}:
                    cleaned_pairs.append(("ssl", "false"))

            self.DATABASE_URL = urlunsplit(
                (parts.scheme, parts.netloc, parts.path, urlencode(cleaned_pairs), parts.fragment)
            )

        if not self.REDIS_ENABLED:
            self.REDIS_URL = None
            return self

        if self.REDIS_URL == "":
            self.REDIS_URL = None
            return self

        if not self.REDIS_URL:
            password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = (
                f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return self

settings = Settings()
