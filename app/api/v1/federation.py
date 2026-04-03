from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import AgentRegistry
from app.services.federation_service import FederationService
from app.core.security import require_scopes, get_current_principal
from typing import Dict, Any, List

router = APIRouter(prefix="/federation", tags=["Federation"], dependencies=[require_scopes([])])

@router.post("/handoff/mcp-to-cli", response_model=Dict[str, Any])
async def handoff_mcp_to_cli(
    mcp_tool_call: Dict[str, Any], 
    request: Request,
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Translates an MCP tool call to CLI execution with session state.
    Keyed by the user's EAT token.
    """
    # Extract EAT token from authorization header if present
    eat_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not eat_token:
        # Fallback to JTI from principal if available
        eat_token = principal.get("jti", "anonymous-session-id")
    
    service = FederationService()
    try:
        cli_exec = await service.mcp_to_cli_handoff(mcp_tool_call, eat_token)
        return cli_exec
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/a2a/broadcast", response_model=List[Dict[str, Any]])
async def broadcast_a2a_discovery(
    peer_endpoints: List[str], 
    db: Session = Depends(get_session)
):
    """
    Broadcasts our discovery card to peer A2A endpoints.
    """
    # Get our system agent (placeholder UUID used in app/main.py)
    # 00000000-0000-0000-0000-000000000001
    from uuid import UUID
    system_agent_id = UUID("00000000-0000-0000-0000-000000000001")
    stmt = select(AgentRegistry).where(AgentRegistry.agent_id == system_agent_id)
    result = await db.execute(stmt)
    my_agent = result.scalars().first()
    
    if not my_agent:
        raise HTTPException(status_code=404, detail="System agent registry entry not found.")
        
    service = FederationService()
    peer_cards = await service.broadcast_a2a_discovery(my_agent, peer_endpoints)
    return peer_cards

@router.post("/acp/delegate", response_model=Dict[str, Any])
async def delegate_to_acp_peer(
    task: Dict[str, Any],
    peer_endpoint: str = Query(...)
):
    """
    Delegates a task to an ACP-compatible peer.
    """
    service = FederationService()
    try:
        result = await service.delegate_to_acp_peer(task, peer_endpoint)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/legacy/execute", response_model=Dict[str, Any])
async def execute_legacy_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """
    Executes a legacy or non-API tool via sandboxed CLI, direct API, or vision fallbacks.
    Feeds all outputs through the unified self-healing + ontology layer.
    """
    service = FederationService()
    try:
        return await service.execute_legacy_tool(tool_name, arguments, metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
