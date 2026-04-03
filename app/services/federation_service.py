from typing import Any, Dict, Optional, List
import structlog
import uuid
from app.services.federation.translator import FederationTranslator
from app.services.federation.discovery import FederationDiscovery
from app.services.federation.session import FederationSession
from app.services.federation.session import FederationSession
from app.services.federation.clients import A2AClient, ACPClient
from app.services.federation.wrappers import AdaptiveWrapper
from app.db.models import AgentRegistry
from app.core.config import settings

logger = structlog.get_logger(__name__)

class FederationService:
    """
    Main service for full cross-protocol federation.
    Coordinates translation, discovery card mapping, ACP messaging,
    and session state management.
    """

    def __init__(self, semantic_mapper: Optional[Any] = None):
        self.translator = FederationTranslator(semantic_mapper)
        self.discovery = FederationDiscovery(self.translator)
        self.wrapper = AdaptiveWrapper(self.translator)

    async def mcp_to_cli_handoff(self, mcp_tool_call: Dict[str, Any], eat_token: str) -> Dict[str, Any]:
        """
        Translates an MCP tool call to CLI execution with session state.
        Permits CLI-local workflows to delegate to MCP-remote agents.
        """
        # 1. Translate tool call
        cli_exec = self.translator.mcp_to_cli(mcp_tool_call)
        
        # 2. Maintain session state keyed by EAT token (or JTI)
        # Assuming we can extract JTI from EAT (simplified for this module)
        jti = self._extract_jti(eat_token)
        session = FederationSession(jti)
        
        await session.update_state("artifacts", mcp_tool_call.get("artifacts", {}))
        await session.update_state("context", mcp_tool_call.get("context", {}))
        await session.update_state("outputs", {})
        
        logger.info("MCP-to-CLI handoff complete", jti=jti, command=cli_exec.get("command"))
        return cli_exec

    async def cli_to_mcp_handoff(self, cli_execution: Dict[str, Any], eat_token: str) -> Dict[str, Any]:
        """
        Translates a CLI execution back to an MCP representation.
        """
        mcp_tool = self.translator.cli_to_mcp(cli_execution)
        jti = self._extract_jti(eat_token)
        session = FederationSession(jti)
        
        # Retrieve session state to enrich the MCP representation
        state = await session.get_state()
        mcp_tool["artifacts"] = state.get("artifacts", {})
        mcp_tool["context"] = state.get("context", {})
        
        logger.info("CLI-to-MCP handoff complete", jti=jti, tool=mcp_tool.get("name"))
        return mcp_tool

    async def broadcast_a2a_discovery(self, my_agent: AgentRegistry, peer_endpoints: List[str]) -> List[Dict[str, Any]]:
        """
        Broadcasts our discovery card to a list of peer A2A endpoints.
        """
        responses = []
        for endpoint in peer_endpoints:
            client = A2AClient(endpoint)
            try:
                peer_card = await client.exchange_discovery_card(my_agent)
                responses.append(peer_card)
            except Exception as e:
                logger.error("Failed A2A discovery exchange", peer=endpoint, error=str(e))
                
        return responses

    async def delegate_to_acp_peer(self, task: Dict[str, Any], peer_endpoint: str) -> Dict[str, Any]:
        """
        Delegates an arbitrary task to an ACP-compatible peer.
        """
        client = ACPClient(peer_endpoint)
        return await client.send_acp_task(task)

    async def execute_legacy_tool(self, tool_name: str, arguments: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """ Executes a legacy/non-API tool via the adaptive wrapper. """
        return await self.wrapper.execute_legacy_tool(tool_name, arguments, metadata)

    def _extract_jti(self, eat_token: str) -> str:
        """
        Mock JTI extraction for demonstration. 
        In actual use, PyJWT.decode would be used here.
        """
        import hashlib
        return hashlib.sha256(eat_token.encode()).hexdigest()[:16]
