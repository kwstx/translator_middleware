import httpx
import structlog
from typing import Any, Dict, Optional, List
from uuid import UUID
from .base import BaseConnector
from app.services.credentials import CredentialService
from app.core.config import settings

logger = structlog.get_logger(__name__)

class ClaudeConnector(BaseConnector):
    """
    Connector for Anthropic Claude.
    Translates Engram's unified MCP task format into Anthropic's Messages API format.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="CLAUDE")
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.base_url = "https://api.anthropic.com/v1/messages"

    def translate_to_tool(self, engram_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP -> Anthropic Messages API.
        Expected MCP format: {"coord": "research", "content": "How far is the moon?"}
        """
        prompt = engram_task.get("content", engram_task.get("coord", ""))
        
        # Build Anthropic message structure
        return {
            "model": engram_task.get("model", "claude-3-haiku-20240307"),
            "max_tokens": engram_task.get("max_tokens", 1024),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            # If the original task had system instructions, we put them in the system field
            "system": engram_task.get("instructions", "You are a helpful AI assistant.")
        }

    def translate_from_tool(self, tool_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anthropic Response -> Engram Unified Format.
        """
        # Extract text content from Anthropic response structure
        content_items = tool_response.get("content", [])
        text = "".join([item.get("text", "") for item in content_items if item.get("type") == "text"])
        
        return {
            "status": "success",
            "protocol": "MCP",
            "payload": {
                "coord": "response",
                "content": text,
                "usage": tool_response.get("usage", {})
            },
            "metadata": {
                "tool": "claude",
                "model": tool_response.get("model", "")
            }
        }

    async def call_tool(self, tool_request: Dict[str, Any], db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs the actual API call to Anthropic Claude.
        If 'db' and 'user_id' are provided, it uses the user's specific API key.
        """
        # Retrieve active token (with auto-refresh)
        api_key = await self.get_active_token(db, user_id, self.api_key)

        if not api_key:
            logger.warning("ClaudeConnector: missing API key, returning mock response")
            return self._mock_call(tool_request)

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, json=tool_request, headers=headers)
            response.raise_for_status()
            return response.json()

    def _mock_call(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a mock response if no API key is provided.
        """
        prompt = tool_request["messages"][0]["content"]
        return {
            "id": "msg_01XvK8V6n6eR8B69H6pG",
            "type": "message",
            "role": "assistant",
            "model": tool_request.get("model", ""),
            "content": [
                {
                    "type": "text",
                    "text": f"[MOCK] This is a response from Claude to your prompt: '{prompt}'"
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }
