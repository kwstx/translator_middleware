import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session
from typing import Any, Dict, Optional, List
from pydantic import BaseModel

from app.db.session import get_session
from app.core.security import get_current_principal
from app.messaging.multi_agent_orchestrator import MultiAgentOrchestrator
from app.core.exceptions import HandoffAuthorizationError

router = APIRouter()
logger = structlog.get_logger(__name__)

class OrchestrateRequest(BaseModel):
    task: str
    metadata: Optional[Dict[str, Any]] = None

class OrchestrateResponse(BaseModel):
    status: str
    correlation_id: str
    results: Dict[str, Any]
    normalized_output: Dict[str, Any]

@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_task(
    request: OrchestrateRequest,
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Entry point for Multi-Agent Orchestration.
    Submits a complex natural language task, parses it, executes subtasks,
    and returns a merged result.
    """
    eat = principal.get("_raw_token")
    if not eat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Engram Access Token (EAT) from Authorization header."
        )

    orchestrator = MultiAgentOrchestrator()
    
    try:
        result = await orchestrator.execute_task(
            user_task=request.task,
            eat=eat,
            db=db
        )
        
        if result.get("status") == "error":
            logger.error("Multi-agent orchestration failed", error=result.get("error"))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result
            )
            
        return result
        
    except HandoffAuthorizationError as e:
        logger.warning("Orchestration unauthorized", user_id=principal.get("sub"), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Orchestration error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestration engine failed: {str(e)}"
        )
