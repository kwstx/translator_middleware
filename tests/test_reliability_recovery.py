import pytest
import asyncio
from unittest.mock import MagicMock, patch
from reliability.middleware import (
    _circuit_breaker, 
    BREAKER_THRESHOLD, 
    COOLDOWN_SECONDS,
    _last_failure_time
)
from bridge.router import routeTo
from app.core.exceptions import (
    RateLimitError, 
    NetworkError, 
    ExpiredTokenError, 
    InvalidCredentialsError,
    PermanentError
)

@pytest.mark.asyncio
async def test_retry_on_transient_rate_limit():
    """
    Verify that ReliabilityMiddleware retries on RateLimitError (via engram_code or exception).
    """
    _circuit_breaker["CLAUDE"] = 0
    
    with patch("app.messaging.orchestrator.Orchestrator.handoff_async") as mock_handoff:
        mock_handoff.side_effect = [
            MagicMock(translated_message={
                "status": "error",
                "error_type": "RateLimitError",
                "engram_code": "TRANSIENT_TOOL_ERROR",
                "detail": "Wait 5s"
            }),
            MagicMock(translated_message={
                "status": "error",
                "error_type": "RateLimitError",
                "engram_code": "TRANSIENT_TOOL_ERROR",
                "detail": "Wait 2s"
            }),
            MagicMock(translated_message={
                "status": "success",
                "payload": {"answer": 42}
            })
        ]
        
        result = await routeTo("CLAUDE", {"task": "test retry"}, correlation_id="test_retry_id")
        
        assert result["status"] == "success"
        assert result["payload"]["answer"] == 42
        assert mock_handoff.call_count == 3

@pytest.mark.asyncio
async def test_stop_on_expired_token():
    """
    Verify that ReliabilityMiddleware stops immediately and returns actionable feedback
    when an ExpiredTokenError occurs.
    """
    _circuit_breaker["SLACK"] = 0
    
    with patch("app.messaging.orchestrator.Orchestrator.handoff_async") as mock_handoff:
        mock_handoff.return_value = MagicMock(translated_message={
            "status": "error",
            "error_type": "ExpiredTokenError",
            "detail": "Session ended",
            "action_required": "REFRESH_CREDENTIALS"
        })
        
        result = await routeTo("SLACK", {"message": "hello"}, correlation_id="test_expired_id")
        
        assert result["status"] == "error"
        assert result["error"] == "token_expired"
        assert result["action_required"] == "REFRESH_CREDENTIALS"
        assert mock_handoff.call_count == 1

@pytest.mark.asyncio
async def test_circuit_breaker_trips():
    """
    Verify that the circuit breaker trips after BREAKER_THRESHOLD failures.
    """
    target = "FAILING_TOOL"
    _circuit_breaker[target] = 0
    
    with patch("app.messaging.orchestrator.Orchestrator.handoff_async") as mock_handoff:
        mock_handoff.return_value = MagicMock(translated_message={
            "status": "error",
            "error_type": "InternalServerError",
            "detail": "Crash"
        })
        
        for i in range(BREAKER_THRESHOLD):
            await routeTo(target, {"ping": i}, correlation_id=f"cb_trip_{i}")
        
        assert _circuit_breaker[target] == BREAKER_THRESHOLD
        
        mock_handoff.reset_mock()
        result = await routeTo(target, {"ping": "blocked"}, correlation_id="cb_blocked")
        
        assert result["status"] == "error"
        assert result["error"] == "circuit_breaker_open"
        assert mock_handoff.call_count == 0

@pytest.mark.asyncio
async def test_invalid_request_schema():
    """
    Verify handled invalid request scenarios (non-retriable).
    """
    _circuit_breaker["PERPLEXITY"] = 0
    
    with patch("app.messaging.orchestrator.Orchestrator.handoff_async") as mock_handoff:
        mock_handoff.return_value = MagicMock(translated_message={
            "status": "error",
            "engram_code": "BAD_TOOL_REQUEST",
            "detail": "Missing field 'query'"
        })
        
        result = await routeTo("PERPLEXITY", {"bad": "request"}, correlation_id="test_bad_req")
        
        assert result["status"] == "error"
        assert result["engram_code"] == "BAD_TOOL_REQUEST"
        assert mock_handoff.call_count == 1

@pytest.mark.asyncio
async def test_network_failure_multi_hop():
    """
    Simulate a network failure during a multi-hop handoff.
    """
    _circuit_breaker["MIROFISH"] = 0
    
    with patch("app.messaging.orchestrator.Orchestrator.handoff_async") as mock_handoff:
        mock_handoff.side_effect = [
            MagicMock(translated_message={
                "status": "error",
                "error_type": "NetworkError",
                "detail": "Connection reset"
            }),
            MagicMock(translated_message={
                "status": "success",
                "payload": "Fish found"
            })
        ]
        
        result = await routeTo("MIROFISH", {"find": "tuna"}, correlation_id="test_network_id")
        
        assert result["status"] == "success"
        assert mock_handoff.call_count == 2
