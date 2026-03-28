import asyncio
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add current directory to sys.path
sys.path.insert(0, os.getcwd())

# Mock external dependencies
sys.modules["pyswip"] = MagicMock()
sys.modules["pyswip"].Prolog.return_value = MagicMock()
sys.modules["pyswip"].Prolog.return_value.query.return_value = []
sys.modules["owlready2"] = MagicMock()
sys.modules["pyDatalog"] = MagicMock()

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

async def run_reliability_tests():
    print("Starting Reliability Tests...")
    
    # Target the specific instance used in the router
    import bridge.router
    print(f"DEBUG: _orchestrator={bridge.router._orchestrator}")
    
    # 1. Test Retry on Rate Limit
    print("\n[1/5] Testing Retry on Rate Limit (Transient)...")
    _circuit_breaker["CLAUDE"] = 0
    with patch.object(bridge.router._orchestrator, "handoff_async") as mock_handoff:
        mock_handoff.side_effect = [
            MagicMock(translated_message={"status": "error", "error_type": "RateLimitError", "engram_code": "TRANSIENT_TOOL_ERROR", "detail": "Wait 5s"}),
            MagicMock(translated_message={"status": "success", "payload": {"answer": 42}})
        ]
        try:
            result = await routeTo("CLAUDE", {"task": "test retry"}, correlation_id="test_retry_id")
            print(f"DEBUG: mock_handoff.call_count={mock_handoff.call_count}")
            if result.get("status") != "success":
                print(f"DEBUG: result was {result}")
            assert result["status"] == "success", f"Expected success, got {result.get('status')}"
            assert result["payload"]["answer"] == 42
            assert mock_handoff.call_count == 2, f"Expected 2 calls, got {mock_handoff.call_count}"
            print("PASS: Retry on Rate Limit Success")
        except AssertionError as e:
            print(f"FAIL: Retry on Rate Limit failed: {e}")
            raise

    # 2. Test Stop on Expired Token
    print("\n[2/5] Testing Stop on Expired Token (Permanent)...")
    _circuit_breaker["SLACK"] = 0
    with patch.object(bridge.router._orchestrator, "handoff_async") as mock_handoff:
        mock_handoff.return_value = MagicMock(translated_message={"status": "error", "error_type": "ExpiredTokenError", "detail": "Session ended", "action_required": "REFRESH_CREDENTIALS"})
        try:
            result = await routeTo("SLACK", {"message": "hello"}, correlation_id="test_expired_id")
            assert result["status"] == "error", f"Expected error, got {result.get('status')}"
            assert result["error"] == "token_expired", f"Expected token_expired, got {result.get('error')}"
            assert result["action_required"] == "REFRESH_CREDENTIALS"
            assert mock_handoff.call_count == 1
            print("PASS: Stop on Expired Token Success")
        except AssertionError as e:
            print(f"FAIL: Stop on Expired Token failed: {e}")
            raise

    # 3. Test Circuit Breaker Trips
    print("\n[3/5] Testing Circuit Breaker Trips...")
    target = "FAILING_TOOL"
    _circuit_breaker[target] = 0
    with patch.object(bridge.router._orchestrator, "handoff_async") as mock_handoff:
        mock_handoff.return_value = MagicMock(translated_message={"status": "error", "error_type": "InternalServerError", "detail": "Crash"})
        try:
            for i in range(BREAKER_THRESHOLD):
                await routeTo(target, {"ping": i}, correlation_id=f"cb_trip_{i}")
            assert _circuit_breaker[target] == BREAKER_THRESHOLD, f"Expected CB to be {BREAKER_THRESHOLD}, but it's {_circuit_breaker[target]}"
            
            mock_handoff.reset_mock()
            result = await routeTo(target, {"ping": "blocked"}, correlation_id="cb_blocked")
            assert result["status"] == "error"
            assert result["error"] == "circuit_breaker_open"
            assert mock_handoff.call_count == 0
            print("PASS: Circuit Breaker Success")
        except AssertionError as e:
            print(f"FAIL: Circuit Breaker failed: {e}")
            raise

    # 4. Test Invalid Request Handling
    print("\n[4/5] Testing Invalid Request Schema...")
    _circuit_breaker["PERPLEXITY"] = 0
    with patch.object(bridge.router._orchestrator, "handoff_async") as mock_handoff:
        mock_handoff.return_value = MagicMock(translated_message={"status": "error", "engram_code": "BAD_TOOL_REQUEST", "detail": "Missing field 'query'"})
        try:
            result = await routeTo("PERPLEXITY", {"bad": "request"}, correlation_id="test_bad_req")
            assert result["status"] == "error"
            assert result["engram_code"] == "BAD_TOOL_REQUEST"
            assert mock_handoff.call_count == 1
            print("PASS: Invalid Request Success")
        except AssertionError as e:
            print(f"FAIL: Invalid Request failed: {e}")
            raise

    # 5. Test Network Failure with Reconnect Guidance
    print("\n[5/5] Testing Network Failure Guidance...")
    _circuit_breaker["MIROFISH"] = 0
    with patch.object(bridge.router._orchestrator, "handoff_async") as mock_handoff:
        mock_handoff.side_effect = [
            MagicMock(translated_message={"status": "error", "error_type": "NetworkError", "detail": "Connection reset"}),
            MagicMock(translated_message={"status": "success", "payload": "Fish found"})
        ]
        try:
            result = await routeTo("MIROFISH", {"find": "tuna"}, correlation_id="test_network_id")
            assert result["status"] == "success"
            assert mock_handoff.call_count == 2
            print("PASS: Network Failure Guidance Success")
        except AssertionError as e:
            print(f"FAIL: Network Failure failed: {e}")
            raise

    print("\nALL RELIABILITY TESTS PASSED!")

if __name__ == "__main__":
    try:
        asyncio.run(run_reliability_tests())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
