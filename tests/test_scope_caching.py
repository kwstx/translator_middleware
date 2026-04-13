import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from engram_sdk.scope import Scope, ScopeCache

def test_scope_cache_local_logic(tmp_path):
    """Verifies that ScopeCache correctly saves and loads from local filesystem."""
    cache_dir = tmp_path / "engram_test_scopes"
    cache = ScopeCache(cache_dir=str(cache_dir))
    
    tools = ["tool1", "tool2"]
    corrected = {"tool1": {"type": "correction", "val": 123}}
    
    # Ensure cache is empty
    assert cache.get(tools) is None
    
    # Store in cache
    cache.set(tools, corrected, {"tool1": "CLI", "tool2": "MCP"})
    
    # Retrieve from cache
    cached = cache.get(tools)
    assert cached is not None
    assert cached["corrected_schemas"] == corrected
    assert cached["routing_decisions"] == {"tool1": "CLI", "tool2": "MCP"}
    assert "timestamp" in cached
    assert sorted(cached["tools"]) == sorted(tools)
    
    # Verify persistence by creating a new cache instance pointing to same dir
    new_cache = ScopeCache(cache_dir=str(cache_dir))
    cached_persistent = new_cache.get(tools)
    assert cached_persistent["corrected_schemas"] == corrected
    assert cached_persistent["routing_decisions"] == {"tool1": "CLI", "tool2": "MCP"}

def test_scope_validation_uses_cache(monkeypatch):
    """Verifies that Scope.validate hits the cache and avoids redundant backend calls."""
    # Mock SDK
    mock_sdk = MagicMock()
    mock_sdk.transport = MagicMock()
    
    # Create a local cache for testing
    test_cache_dir = Path("./tmp_test_cache_validation")
    if test_cache_dir.exists():
        shutil.rmtree(test_cache_dir)
    
    cache = ScopeCache(cache_dir=str(test_cache_dir))
    mock_sdk.scope_cache = cache
    
    # Mock transport for batch validation
    correction_data = {"tool1": {"status": "updated"}}
    mock_sdk.transport.request_json.return_value = {
        "results": {
            "tool1": {
                "drift": True,
                "corrected_schema": correction_data["tool1"],
                "best_backend": "CLI"
            }
        }
    }
    
    tools = ["tool1"]
    scope1 = Scope(tools=tools)
    
    # First validation: should call /registry/scope/validate via transport
    res1 = scope1.validate(mock_sdk)
    assert res1 is False # drift found
    assert mock_sdk.transport.request_json.call_count == 1
    assert scope1.corrected_schemas == correction_data
    assert scope1.routing_decisions == {"tool1": "CLI"}
    assert scope1.validation_timestamp is not None
    
    # Reset mock call count
    mock_sdk.transport.request_json.reset_mock()
    
    # Second validation with a NEW scope object but SAME tools
    scope2 = Scope(tools=tools)
    res2 = scope2.validate(mock_sdk)
    
    assert res2 is False # Should still find drift (from cache)
    assert mock_sdk.transport.request_json.call_count == 0 # CACHE HIT: No transport call
    assert scope2.corrected_schemas == correction_data
    assert scope2.routing_decisions == {"tool1": "CLI"}
    assert scope2.validation_timestamp is not None
    
    # Clean up
    if test_cache_dir.exists():
        shutil.rmtree(test_cache_dir)

def test_scope_cache_hash_collision_avoidance():
    """Ensures different tool lists produce different cache entries."""
    cache = ScopeCache(cache_dir="./tmp_test_collision")
    
    tools_a = ["tool1", "tool2"]
    tools_b = ["tool1", "tool3"]
    
    cache.set(tools_a, {"a": 1}, {"tool1": "CLI"})
    cache.set(tools_b, {"b": 2}, {"tool1": "MCP"})
    
    assert cache.get(tools_a)["corrected_schemas"] == {"a": 1}
    assert cache.get(tools_b)["corrected_schemas"] == {"b": 2}
    
    if os.path.exists("./tmp_test_collision"):
        shutil.rmtree("./tmp_test_collision")

def test_scope_activation_sdk_call():
    """Verifies that scope.activate correctly calls the registry endpoint."""
    mock_sdk = MagicMock()
    mock_sdk.transport = MagicMock()
    mock_sdk.transport.request_json.return_value = {"status": "ok"}
    
    tools = ["tool1", "tool2"]
    scope = Scope(tools=tools, step_id="step-123")
    scope.corrected_schemas = {"tool1": {"type": "object"}}
    scope.validation_timestamp = 123456789.0
    
    success = scope.activate(mock_sdk)
    
    assert success is True
    mock_sdk.transport.request_json.assert_called_once()
    args, kwargs = mock_sdk.transport.request_json.call_args
    assert args[0] == "POST"
    assert args[1] == "/registry/scope/activate"
    assert kwargs["json_body"]["scope_id"] == "step-123"
    assert kwargs["json_body"]["tools"] == tools
    assert kwargs["json_body"]["corrected_schemas"] == scope.corrected_schemas
    assert kwargs["json_body"]["routing_decisions"] == scope.routing_decisions
