import sys
from unittest.mock import MagicMock
sys.modules["pyswip"] = MagicMock()

import pytest
import jwt
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.db.session import get_session
from app.db.models import User, PermissionProfile
from app.core.security import create_engram_access_token, check_permissions, get_current_principal

@pytest.fixture
def client():
    return TestClient(app)

def test_create_engram_access_token():
    user_id = str(uuid4())
    permissions = {
        "tool_a": ["read", "write"],
        "tool_b": ["execute"]
    }
    
    token = create_engram_access_token(user_id, permissions)
    assert isinstance(token, str)
    
    # Decode and verify
    from app.core.config import settings
    payload = jwt.decode(
        token, 
        settings.AUTH_JWT_SECRET, 
        algorithms=[settings.AUTH_JWT_ALGORITHM],
        audience=settings.AUTH_AUDIENCE,
        issuer=settings.AUTH_ISSUER
    )
    
    assert payload["sub"] == user_id
    assert payload["type"] == "EAT"
    assert "tool_a" in payload["allowed_tools"]
    assert "tool_b" in payload["allowed_tools"]
    assert payload["scopes"]["tool_a"] == ["read", "write"]
    assert "read" in payload["scope"]
    assert "write" in payload["scope"]
    assert "execute" in payload["scope"]

@pytest.mark.asyncio
async def test_generate_eat_endpoint(client):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    
    user_id = uuid4()
    mock_user_id_str = str(user_id)
    
    # Mock current principal (the caller)
    mock_principal = {"sub": mock_user_id_str, "scope": "translate:a2a"}
    app.dependency_overrides[get_current_principal] = lambda: mock_principal
    
    # Mock PermissionProfile lookup
    mock_profile = PermissionProfile(
        user_id=user_id,
        permissions={"agent_x": ["read"]}
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_profile
    mock_session.execute.return_value = mock_result
    
    response = client.post("/api/v1/auth/tokens/generate-eat")
    
    assert response.status_code == 200
    assert "eat" in response.json()
    
    # Verify the token type in response
    payload = jwt.decode(
        response.json()["eat"],
        options={"verify_signature": False} # Just checking payload here
    )
    assert payload["type"] == "EAT"
    assert payload["scopes"] == {"agent_x": ["read"]}
    
    app.dependency_overrides.pop(get_session)
    app.dependency_overrides.pop(get_current_principal)

@pytest.mark.asyncio
async def test_check_permissions_with_eat():
    user_id = str(uuid4())
    eat_payload = {
        "sub": user_id,
        "type": "EAT",
        "scopes": {
            "trading_view": ["read", "execute"]
        }
    }
    
    # Test success from token (DB should not be called at all)
    result = await check_permissions(
        tool_id="trading_view",
        scope="execute",
        db=None,
        principal=eat_payload
    )
    assert result is True
    
    # Test failure - scope not in token, so falls back to DB which says no profile
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await check_permissions(
            tool_id="trading_view",
            scope="admin",
            db=mock_db,
            principal=eat_payload
        )
    assert exc.value.status_code == 403
    assert mock_db.execute.called # Ensures fallback occurred
    
    # Test tool not in token - falls back to DB
    mock_db.execute.reset_mock()
    with pytest.raises(HTTPException) as exc:
        await check_permissions(
            tool_id="unknown_tool",
            scope="read",
            db=mock_db,
            principal=eat_payload
        )
    assert exc.value.status_code == 403
    assert mock_db.execute.called
