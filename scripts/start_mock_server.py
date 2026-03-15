import uvicorn
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
from app.main import app
from app.db.session import get_session
from app.core.security import get_current_principal, oauth2_scheme

async def mock_get_session():
    yield AsyncMock()

async def mock_principal():
    return {"sub": "test_user", "scope": "translate:a2a translate:beta"}

async def mock_token():
    return "test-token"

# Override dependencies
app.dependency_overrides[get_session] = mock_get_session
app.dependency_overrides[get_current_principal] = mock_principal
app.dependency_overrides[oauth2_scheme] = mock_token

from app.api.v1.endpoints import poll_agent_messages
async def mock_poll(agent_id, lease_seconds, db):
    # Always return a mock message for testing
    return {
        "message_id": str(uuid.uuid4()),
        "task_id": str(uuid.uuid4()),
        "payload": {
            "intent": "status_update",
            "status": "active"
        },
        "leased_until": "2026-03-15T22:00:00Z"
    }

app.dependency_overrides[poll_agent_messages] = mock_poll

# Dummy lifespan to avoid background services
@asynccontextmanager
async def dummy_lifespan(app):
    yield

app.router.lifespan_context = dummy_lifespan

if __name__ == "__main__":
    print("Starting Mock Engram Server on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
