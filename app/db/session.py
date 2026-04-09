import os
from urllib.parse import parse_qsl, urlsplit, urlunsplit
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from app.core.config import settings
from typing import AsyncGenerator
import asyncio
import logging

# Prevent libpq-style env vars from leaking into asyncpg
for key in ("PGSSLMODE", "PGCHANNELBINDING", "PGSSLROOTCERT", "PGSSLCERT", "PGSSLKEY", "PGSSLCRL"):
    os.environ.pop(key, None)

def _sanitize_db_url(url: str) -> tuple[str, bool]:
    if url.startswith("sqlite"):
        return url, False
    parts = urlsplit(url)
    raw_pairs = parse_qsl(parts.query, keep_blank_values=True)
    cleaned_pairs = []
    ssl_required = False
    for key, value in raw_pairs:
        key_clean = key.strip().lower()
        value_clean = value.strip().strip("\"'")
        if key_clean in {"sslmode", "channel_binding", "sslrootcert", "sslcert", "sslkey", "sslcrl"}:
            if key_clean == "sslmode" and value_clean in {"require", "verify-full", "verify-ca"}:
                ssl_required = True
            continue
        if key_clean == "ssl" and value_clean.lower() in {"true", "1", "yes"}:
            ssl_required = True
            continue
        cleaned_pairs.append((key.strip(), value_clean))

    # Neon requires SSL; avoid passing sslmode to asyncpg
    if "neon.tech" in (parts.netloc or ""):
        ssl_required = True

    # Drop all query params to avoid asyncpg parsing libpq options
    sanitized = urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))
    return sanitized, ssl_required

# Use SQLModel engines for compatibility
db_url, ssl_required = _sanitize_db_url(settings.DATABASE_URL)
connect_args = {"ssl": True} if ssl_required else {}
engine = create_async_engine(db_url, echo=False, future=True, connect_args=connect_args)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

logger = logging.getLogger(__name__)

async def init_db():
    """
    Initializes the database connection and runs migrations.
    - PostgreSQL (production/Docker): Uses Alembic migrations.
    - SQLite (local dev): Uses SQLModel.metadata.create_all directly,
      since Alembic migrations use PostgreSQL-specific types (JSONB, ARRAY).
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    retries = 2 if is_sqlite else 15
    delay = 1 if is_sqlite else 4

    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

                if is_sqlite:
                    # Optimized production settings for SQLite
                    await conn.execute(text("PRAGMA journal_mode=WAL"))
                    await conn.execute(text("PRAGMA synchronous=NORMAL"))
                    
                    # SQLite: skip Alembic (migrations use pg-only types).
                    # Import all models so SQLModel.metadata knows every table.
                    import app.db.models  # noqa: F401
                    try:
                        import app.catalog.models  # noqa: F401
                    except Exception:
                        pass
                    await conn.run_sync(SQLModel.metadata.create_all)
                    logger.info("SQLite database tables initialized in WAL mode via SQLModel.metadata.create_all.")
                else:
                    # PostgreSQL: full Alembic migration path
                    await conn.execute(text("SELECT pg_advisory_xact_lock(42)"))
                    logger.info("Database connection established. Running migrations...")

                    from alembic.config import Config
                    from alembic import command

                    def run_upgrade():
                        try:
                            logger.info("Alembic: Loading config...")
                            alembic_cfg = Config("alembic.ini")
                            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
                            logger.info("Alembic: Running upgrade head...")
                            command.upgrade(alembic_cfg, "head")
                            logger.info("Alembic: Upgrade completed.")
                        except Exception as ex:
                            logger.error("Alembic: Upgrade failed", error=str(ex))
                            raise ex

                    await asyncio.to_thread(run_upgrade)

            logger.info("Database initialized successfully.")
            return
        except Exception as e:
            if i < retries - 1:
                logger.warning(f"Database initialization failed (attempt {i+1}/{retries}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Database initialization failed after {retries} attempts. Exiting.")
                raise e
