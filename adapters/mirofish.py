from .base import EngramAdapter as BaseAdapter
import uuid
import httpx
from typing import Any, Dict, Optional

class EngramAdapter(BaseAdapter):
    """
    MiroFish specialization of the EngramAdapter.
    Automatically registers the MiroFish bridge agent on initialization.
    Uses the pipe_to_mirofish logic for routing.
    """
    def __init__(self, engram_url: str):
        config = {
            "agent_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "mirofish.swarm")),
            "supported_protocols": ["MIROFISH"],
            "capabilities": ["swarm_simulation", "predictive_analytics"],
            "semantic_tags": ["mirofish", "swarm", "bridge"],
            "endpoint_url": "http://localhost:5001" # Default MiroFish bridge port
        }
        super().__init__(engram_url, agent_config=config)

    async def routeTo(self, target: str, payload: Any, **options) -> Dict[str, Any]:
        """
        Specialized routeTo that handles MiroFish's specific /pipe endpoint
        when the target is 'mirofish'.
        """
        if target.lower() == "mirofish":
            pipe_url = f"{self.engram_url}/api/v1/mirofish/pipe"
            
            # This mirrors the logic in the TypeScript mirofish-bridge
            request_body = {
                "agent_id": "mirofish-sdk-client",
                "protocol": options.get("source_protocol", "A2A"),
                "payload": {
                    "seed_text": payload if isinstance(payload, str) else payload.get("seed_text", ""),
                    "num_agents": options.get("num_agents", 1000)
                },
                "swarm_id": options.get("swarm_id", "default")
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(pipe_url, json=request_body, timeout=60.0)
                response.raise_for_status()
                return response.json()
        
        # Fallback to base routing
        return await super().routeTo(target, payload, **options)

def init_mirofish(engram_url: str): return EngramAdapter(engram_url)
