import httpx
import structlog
from typing import Any, Dict, Optional, List
from uuid import UUID
from .base import BaseConnector
from app.services.credentials import CredentialService
from app.core.config import settings

logger = structlog.get_logger(__name__)

class PerplexityConnector(BaseConnector):
    """
    Connector for Perplexity.
    Translates Engram's unified MCP task format into Perplexity's API format.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="PERPLEXITY")
        self.api_key = api_key or settings.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai/chat/completions"

    def translate_to_tool(self, engram_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP -> Perplexity Chat Completions API.
        """
        prompt = engram_task.get("content", engram_task.get("coord", ""))
        
        return {
            "model": engram_task.get("model", "llama-3-sonar-small-32k-online"),
            "messages": [
                {"role": "system", "content": "You are a highly accurate search assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": engram_task.get("max_tokens", 512),
            "temperature": 0.2,
            "return_citations": True
        }

    def translate_from_tool(self, tool_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perplexity Response -> Engram Unified Format.
        """
        choices = tool_response.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        citations = tool_response.get("citations", [])
        
        return {
                "status": "success",
                "protocol": "MCP",
                "payload": {
                    "coord": "search_results",
                    "content": content,
                    "citations": citations
                },
                "metadata": {
                    "tool": "perplexity",
                    "model": tool_response.get("model", "")
                }
            }

    async def call_tool(self, tool_request: Dict[str, Any], db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs the actual API call to Perplexity.
        If 'db' and 'user_id' are provided, it uses the user's specific API key.
        """
        api_key = self.api_key

        # Override with user credential if available
        if db and user_id:
            try:
                cred = await CredentialService.get_credential_by_provider(db, UUID(user_id), "perplexity")
                if cred:
                    api_key = CredentialService.decrypt_token(cred)
                    logger.info("PerplexityConnector: using user-provided API key", user_id=user_id)
            except Exception as e:
                logger.warning("PerplexityConnector: failed to retrieve user credentials", error=str(e))

        if not api_key:
            logger.warning("PerplexityConnector: missing API key, returning mock response")
            return self._mock_call(tool_request)

        headers = {
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(self.base_url, json=tool_request, headers=headers)
            response.raise_for_status()
            return response.json()

    def _mock_call(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a mock search result if no API key is provided.
        """
        prompt = tool_request["messages"][1]["content"]
        return {
            "id": "pplx-123456",
            "model": tool_request.get("model", ""),
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"[MOCK] Perplexity search result for '{prompt}'. Grounded in truth."
                    }
                }
            ],
            "citations": ["https://perplexity.ai/faq"]
        }
