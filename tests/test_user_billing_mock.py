import pytest
from uuid import uuid4

from app.messaging.connectors.claude import ClaudeConnector
from app.messaging.connectors.perplexity import PerplexityConnector
from app.services.credentials import CredentialService


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _DummyAsyncClient:
    def __init__(self, captured):
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self._captured["url"] = url
        self._captured["json"] = json
        self._captured["headers"] = headers or {}
        return _DummyResponse(self._captured["response_payload"])


@pytest.mark.asyncio
async def test_claude_connector_uses_user_token(monkeypatch):
    captured = {
        "response_payload": {
            "content": [{"type": "text", "text": "ok"}],
            "model": "claude-3-haiku-20240307",
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    }

    async def _fake_get_active_token(db, user_id, provider_name):
        return "user-claude-key"

    monkeypatch.setattr(CredentialService, "get_active_token", _fake_get_active_token)
    monkeypatch.setattr(
        "app.messaging.connectors.claude.httpx.AsyncClient",
        lambda *args, **kwargs: _DummyAsyncClient(captured),
    )

    connector = ClaudeConnector(api_key="engram-claude-key")
    tool_request = {"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": "hi"}]}

    await connector.call_tool(tool_request, db=object(), user_id=str(uuid4()))

    assert captured["headers"]["x-api-key"] == "user-claude-key"
    assert captured["headers"]["x-api-key"] != "engram-claude-key"


@pytest.mark.asyncio
async def test_perplexity_connector_uses_user_token(monkeypatch):
    captured = {
        "response_payload": {
            "choices": [{"message": {"content": "ok"}}],
            "model": "llama-3-sonar-small-32k-online",
            "citations": [],
        }
    }

    class _FakeCredential:
        encrypted_token = "encrypted-placeholder"

    async def _fake_get_by_provider(db, uid, provider_name):
        return _FakeCredential()

    def _fake_decrypt_token(cred):
        return "user-perplexity-key"

    monkeypatch.setattr(CredentialService, "get_credential_by_provider", _fake_get_by_provider)
    monkeypatch.setattr(CredentialService, "decrypt_token", _fake_decrypt_token)
    monkeypatch.setattr(
        "app.messaging.connectors.perplexity.httpx.AsyncClient",
        lambda *args, **kwargs: _DummyAsyncClient(captured),
    )

    connector = PerplexityConnector(api_key="engram-perplexity-key")
    tool_request = {"model": "llama-3-sonar-small-32k-online", "messages": [{"role": "user", "content": "hi"}]}

    await connector.call_tool(tool_request, db=object(), user_id=str(uuid4()))

    assert captured["headers"]["authorization"] == "Bearer user-perplexity-key"
    assert captured["headers"]["authorization"] != "Bearer engram-perplexity-key"
