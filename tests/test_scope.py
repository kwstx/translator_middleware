import pytest
from engram_sdk import Scope

def test_scope_initialization():
    tools = ["tool1", "tool2"]
    scope = Scope(tools=tools)
    
    assert scope.tools == tools
    assert scope.step_id is not None
    assert len(scope.step_id) > 0

def test_scope_explicit_step_id():
    tools = ["tool1"]
    step_id = "test-step-123"
    scope = Scope(tools=tools, step_id=step_id)
    
    assert scope.step_id == step_id

def test_scope_to_dict():
    tools = ["tool1", "tool2"]
    scope = Scope(tools=tools, step_id="mysid")
    data = scope.to_dict()
    
    assert data == {
        "step_id": "mysid",
        "tools": ["tool1", "tool2"]
    }

def test_scope_from_dict():
    data = {
        "step_id": "mysid",
        "tools": ["tool1", "tool2"]
    }
    scope = Scope.from_dict(data)
    
    assert scope.step_id == "mysid"
    assert scope.tools == ["tool1", "tool2"]

def test_scope_contains():
    scope = Scope(tools=["tool1", "tool2"])
    
    assert scope.contains("tool1") is True
    assert scope.contains("tool3") is False

def test_scope_tool_count():
    scope = Scope(tools=["tool1", "tool2", "tool3"])
    assert scope.tool_count == 3
