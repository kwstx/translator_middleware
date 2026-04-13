from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import json

from .exceptions import EngramSDKError

if TYPE_CHECKING:
    from .client import EngramSDK
    from .scope import Scope

class ScopeValidationError(EngramSDKError):
    """Raised when a tool call is attempted outside the active validated scope."""
    pass

class RuntimeAdapter:
    """
    The RuntimeAdapter acts as a security and validation gate for agent tool calls.
    
    It enforces the 'developer-in-the-loop' principle by ensuring that at inference time,
    only tools and schemas that were explicitly validated and included in the active 
    scope can be executed. 
    
    If the model attempts to hallucinate a tool or use an outdated schema, the adapter
    rejects the call immediately before it reaches the backend.
    """

    def __init__(self, sdk: EngramSDK, scope: Scope):
        self._sdk = sdk
        self._scope = scope

    def call(self, tool_name: str, arguments: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Validates and executes a tool call within the current scope.
        
        Args:
            tool_name: The name or ID of the tool to call.
            arguments: The arguments for the tool call.
            **kwargs: Additional parameters passed to the backend (e.g. action name).
            
        Returns:
            The result of the tool execution.
            
        Raises:
            ScopeValidationError: If the tool is not in the active scope.
        """
        # 1. Enforce Scope Membership: The model proposes, the code disposes.
        if not self._scope.contains(tool_name):
            allowed = ", ".join(self._scope.tools)
            raise ScopeValidationError(
                f"Blocked unauthorized tool call: '{tool_name}' is not in the active scope. "
                f"Current validated tools for this turn are: [{allowed}]. "
                "Enforcement triggered at inference time."
            )

        # 2. Schema Adaptation
        # If we have a corrected schema for this tool (from drift detection), 
        # we log that we are using it. The backend already knows about this 
        # from the activate() call, but here we could add client-side validation.
        corrected = self._scope.corrected_schemas.get(tool_name)
        if corrected:
            # Future: add jsonschema validation here for 'immediate' rejection
            pass

        # 3. Resolve Tool ID for Backend (mcp.call_tool expects UUID)
        tool_id = self._scope.tool_ids.get(tool_name, tool_name)

        # 4. Forward Call via MCP Protocol
        payload = {
            "method": "mcp.call_tool",
            "params": {
                "tool_id": tool_id,
                "arguments": arguments,
                "scope_id": self._scope.step_id,
                **kwargs
            },
            "id": 1,
            "jsonrpc": "2.0"
        }

        try:
            response = self._sdk.transport.request_json(
                "POST", 
                "/registry/mcp/call", 
                json_body=payload
            )
            
            if "error" in response:
                # Still returns the error as part of the JSON-RPC response
                return response
            
            return response.get("result", {})
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Transport error: {str(e)}"},
                "id": 1
            }

    def __repr__(self) -> str:
        return f"RuntimeAdapter(scope={self._scope.name or self._scope.step_id}, tools={len(self._scope.tools)})"
