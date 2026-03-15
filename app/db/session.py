import os
from urllib.parse import parse_qsl, urlsplit, urlunsplit
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from app.core.config import settings
from typing import AsyncGenerator

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
engine = create_async_engine(db_url, echo=True, future=True, connect_args=connect_args)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        # Import models here to make sure they are registered with SQLModel.metadata
        from app.db.models import (
            ProtocolMapping,
            ProtocolVersionDelta,
            AgentRegistry,
            SemanticOntology,
            Task,
            AgentMessage,
            MappingFailureLog,
        )
        await conn.run_sync(SQLModel.metadata.create_all)
        if engine.dialect.name == "postgresql":
            await _ensure_timestamptz(conn)


async def _ensure_timestamptz(conn) -> None:
    columns = {
        "protocol_mapping": ["created_at", "updated_at"],
        "protocol_version_delta": ["created_at", "updated_at"],
        "agent_registry": ["last_seen"],
        "semantic_ontology": ["created_at"],
        "tasks": ["leased_until", "created_at", "updated_at", "completed_at", "dead_lettered_at"],
        "agent_messages": ["leased_until", "created_at", "updated_at", "acked_at"],
        "mapping_failure_logs": ["created_at"],
    }

    for table, cols in columns.items():
        for col in cols:
            result = await conn.execute(
                text(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table
                      AND column_name = :column
                    """
                ),
                {"table": table, "column": col},
            )
            data_type = result.scalar()
            if data_type == "timestamp without time zone":
                await conn.execute(
                    text(
                        f"ALTER TABLE {table} "
                        f"ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE "
                        f"USING timezone('UTC', {col})"
                    )
                )
