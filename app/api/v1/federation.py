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

@router.post("/translate", response_model=Dict[str, Any])
async def protocol_translate(
    payload: Dict[str, Any],
    from_proto: str = Query(..., alias="from"),
    to_proto: str = Query(..., alias="to")
):
    """
    Generic bridge for translating any payload between protocols using the ontology.
    """
    service = FederationService()
    try:
        # Normalize protocol names
        f = from_proto.upper()
        t = to_proto.upper()
        
        # Use ontology as an intermediate step
        canonical = service.translator.to_ontology(payload, f)
        translated = service.translator.from_ontology(canonical, t)
        
        return {
            "source_protocol": f,
            "target_protocol": t,
            "translated_payload": translated,
            "canonical_bridge": canonical
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/handoff/simulate", response_model=Dict[str, Any])
async def handoff_simulate(
    source_agent: str,
    target_agent: str,
    request: Request,
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Simulates a multi-agent handoff and returns semantic state details.
    """
    eat_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not eat_token:
        eat_token = principal.get("jti", "sim-session-id")
    
    service = FederationService()
    try:
        # Simulate a handoff by updating session state with mock data
        jti = service._extract_jti(eat_token)
        session = FederationSession(jti)
        
        mock_artifacts = {"message": f"Handoff from {source_agent}", "status": "active"}
        mock_context = {"priority": "high", "agent_stack": [source_agent]}
        
        await session.update_state("artifacts", mock_artifacts)
        await session.update_state("context", mock_context)
        
        state = await session.get_state()
        
        return {
            "source": source_agent,
            "target": target_agent,
            "session_id": jti,
            "transferred_state": state,
            "semantic_readiness": "Verified",
            "bridged_protocols": ["MCP", "CLI", "A2A", "ACP"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
