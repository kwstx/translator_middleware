from .base import EngramAdapter as BaseAdapter
import uuid

class EngramAdapter(BaseAdapter):
    """
    OpenClaw specialization of the EngramAdapter.
    Automatically registers a default OpenClaw agent on initialization.
    """
    def __init__(self, engram_url: str):
        config = {
            "agent_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "openclaw.agent")),
            "supported_protocols": ["A2A", "MCP"],
            "capabilities": ["prediction", "analysis", "market_intelligence"],
            "semantic_tags": ["openclaw", "alpha", "swarm"],
            "endpoint_url": "http://localhost:8001" # Default endpoint for OpenClaw agents
        }
        super().__init__(engram_url, agent_config=config)

def init_openclaw(engram_url: str): return EngramAdapter(engram_url)
