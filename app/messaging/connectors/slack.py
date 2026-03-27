import httpx
import structlog
from typing import Any, Dict, Optional, List
from uuid import UUID
from .base import BaseConnector
from app.services.credentials import CredentialService
from app.core.config import settings

logger = structlog.get_logger(__name__)

class SlackConnector(BaseConnector):
    """
    Connector for Slack.
    Translates Engram's unified MCP task format into Slack API format.
    """

    def __init__(self, api_token: Optional[str] = None):
        super().__init__(name="SLACK")
        self.api_token = api_token or settings.SLACK_API_TOKEN
        self.base_url = "https://slack.com/api/chat.postMessage"

    def translate_to_tool(self, engram_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP -> Slack API format (chat.postMessage).
        Expected MCP task: {"coord": "notify", "channel": "#general", "content": "Hello Slack!"}
        """
        prompt = engram_task.get("content", engram_task.get("coord", ""))
        channel = engram_task.get("channel", "#general")
        
        return {
            "channel": channel,
            "text": f"*Engram Notification*\n{prompt}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{engram_task.get('title', 'Engram Activity')}*\n{prompt}"
                    }
                }
            ]
        }

    def translate_from_tool(self, tool_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Slack Response -> Engram Unified Format.
        """
        ok = tool_response.get("ok", False)
        ts = tool_response.get("ts", "")
        error = tool_response.get("error", "unknown")
        
        return {
                "status": "success" if ok else "error",
                "protocol": "MCP",
                "payload": {
                    "coord": "slack_ack",
                    "ok": ok,
                    "timestamp": ts,
                    "error": error if not ok else None
                },
                "metadata": {
                    "tool": "slack",
                    "channel": tool_response.get("channel", "")
                }
            }

    async def call_tool(self, tool_request: Dict[str, Any], db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs the actual API call to Slack.
        If 'db' and 'user_id' are provided, it uses the user's specific Slack token.
        """
        api_token = self.api_token

        # Override with user credential if available
        if db and user_id:
            try:
                cred = await CredentialService.get_credential_by_provider(db, UUID(user_id), "slack")
                if cred:
                    api_token = CredentialService.decrypt_token(cred)
                    logger.info("SlackConnector: using user-provided API token", user_id=user_id)
            except Exception as e:
                logger.warning("SlackConnector: failed to retrieve user credentials", error=str(e))

        if not api_token:
            logger.warning("SlackConnector: missing API token, returning mock response")
            return self._mock_call(tool_request)

        headers = {
            "authorization": f"Bearer {api_token}",
            "content-type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.base_url, json=tool_request, headers=headers)
            response.raise_for_status()
            return response.json()

    def _mock_call(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a mock ACK if no API token is provided.
        """
        return {
            "ok": True,
            "channel": tool_request.get("channel", "#general"),
            "ts": "123456789.0001",
            "message": tool_request.get("text", "")
        }
