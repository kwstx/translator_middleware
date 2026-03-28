from __future__ import annotations

import os
import uuid
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_ENDPOINT_URL = "http://localhost:8080"

_ROOT = Path(__file__).resolve().parent
_AGENT_ID_FILE = _ROOT / "agent_id.txt"


def get_base_url() -> str:
    return os.getenv("ENGRAM_BASE_URL", DEFAULT_BASE_URL)


def get_endpoint_url() -> str:
    return os.getenv("ENGRAM_ENDPOINT_URL", DEFAULT_ENDPOINT_URL)


def get_agent_id() -> str:
    env = os.getenv("ENGRAM_AGENT_ID")
    if env:
        return env

    if _AGENT_ID_FILE.exists():
        existing = _AGENT_ID_FILE.read_text().strip()
        if existing:
            return existing

    new_id = str(uuid.uuid4())
    _AGENT_ID_FILE.write_text(new_id)
    return new_id


def get_eat() -> str | None:
    return os.getenv("ENGRAM_EAT")

