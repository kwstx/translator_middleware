import httpx
import uuid
from typing import Any, Dict, Optional

class EngramAdapter:
    def __init__(self, engram_url: str, agent_config: Optional[Dict[str, Any]] = None):
        """
        Initializes the Engram Adapter and optionally registers the agent.
        """
        self.engram_url = engram_url.rstrip("/")
        if agent_config:
            self.register_agent(agent_config)

    def register_agent(self, config: Dict[str, Any]):
        """
        Registers the agent with the Engram bridge.
        """
        registration_url = f"{self.engram_url}/api/v1/register"
        try:
            # We use a synchronous request here for the init phase
            # In a production SDK, this might be handled more robustly
            response = httpx.post(registration_url, json=config, timeout=5.0)
            response.raise_for_status()
        except Exception as e:
            print(f"[Engram] Registration failed: {e}")

    async def routeTo(self, target: str, payload: Any, **options) -> Dict[str, Any]:
        """
        Routes a message to a target protocol or agent via the Engram bridge.
        """
        route_url = f"{self.engram_url}/api/v1/beta/playground/translate"
        
        request_body = {
            "source_protocol": options.get("source_protocol", "A2A"),
            "target_protocol": target,
            "payload": payload
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(route_url, json=request_body, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            return result.get("payload", result)
