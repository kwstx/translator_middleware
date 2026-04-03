import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.db.session import get_session
from app.db.models import ToolFeedback, EvolutionFeedbackType, ToolEvolution
from app.core.security import get_current_principal
from app.services.evolution import ToolEvolutionService

router = APIRouter()
logger = structlog.get_logger(__name__)

class FeedbackSubmit(BaseModel):
    tool_id: uuid.UUID
    score: float = Field(..., ge=-1.0, le=1.0, description="Rating from -1 to 1 or 0 to 1")
    comment: Optional[str] = None
    feedback_type: EvolutionFeedbackType = EvolutionFeedbackType.RATING
    metadata: Dict[str, Any] = {}

class EvolutionResponse(BaseModel):
    id: uuid.UUID
    tool_id: uuid.UUID
    tool_name: Optional[str] = None
    previous_version: str
    new_version: str
    change_type: str
    confidence_score: float
    applied: bool
    diff_payload: Optional[Dict[str, Any]] = None
    evolution_signals: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class StatusResponse(BaseModel):
    pending_count: int
    total_evolutions: int
    pending_proposals: List[EvolutionResponse]
    last_updated: datetime

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_tool_feedback(
    request: FeedbackSubmit,
    db: Any = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Submits feedback (ratings, corrections) to the Evolution Engine via EAT token.
    Used for guidance of the Self-Evolving Tools logic.
    """
    user_id = uuid.UUID(principal["sub"]) if "sub" in principal else None
    eat = principal.get("_raw_token")
    
    feedback = ToolFeedback(
        tool_id=request.tool_id,
        user_id=user_id,
        eat_token=eat,
        score=request.score,
        comment=request.comment,
        feedback_type=request.feedback_type,
        metadata_json=request.metadata
    )
    
    db.add(feedback)
    await db.commit()
    logger.info("Tool feedback registered", tool_id=request.tool_id, score=request.score)
    return {"status": "success", "message": "Feedback recorded for tool evolution audit."}

@router.get("/history/{tool_id}", response_model=List[EvolutionResponse])
async def get_tool_evolution_history(
    tool_id: uuid.UUID,
    db: Any = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Returns the versioned history of improvements for a specific tool.
    """
    from sqlmodel import select
    stmt = select(ToolEvolution).where(ToolEvolution.tool_id == tool_id).order_by(ToolEvolution.applied_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/status", response_model=StatusResponse)
async def get_evolution_status(
    db: Any = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Returns the current ML improvement progress across all tools.
    """
    service = ToolEvolutionService(db)
    return await service.get_evolution_status()

@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_evolution_loop(
    db: Any = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Manually triggers evolution analysis.
    Creates pending proposals in the dashboard.
    """
    service = ToolEvolutionService(db)
    await service.run_evolution_loop()
    return {"status": "accepted", "message": "Evolution pipeline trigger successful."}

@router.post("/apply/{evolution_id}", response_model=EvolutionResponse)
async def apply_tool_evolution(
    evolution_id: uuid.UUID,
    db: Any = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Applies a pending evolution proposal to a tool.
    """
    service = ToolEvolutionService(db)
    evolution = await service.apply_evolution(evolution_id)
    if not evolution:
        raise HTTPException(status_code=404, detail="Pending evolution not found or already applied.")
    return evolution
