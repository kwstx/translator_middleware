from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Dict, Any, Optional
from app.db.session import get_session
from app.db.models import ProtocolMapping, MappingFailureLog
from app.reconciliation.engine import reconciliation_engine
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class DriftStatus(BaseModel):
    id: str
    source_protocol: str
    target_protocol: str
    source_field: str
    suggested_mapping: Optional[str]
    confidence: Optional[float]
    error_type: str
    payload_excerpt: Dict[str, Any]
    created_at: datetime

class MappingStatus(BaseModel):
    source_protocol: str
    target_protocol: str
    semantic_equivalents: Dict[str, str]
    version: int

class ReconciliationStatusResponse(BaseModel):
    pending_drifts: List[DriftStatus]
    active_mappings: List[MappingStatus]

@router.get("/status", response_model=ReconciliationStatusResponse)
async def get_reconciliation_status(db: AsyncSession = Depends(get_session)):
    """
    Returns the current status of semantic drifts and applied mappings.
    """
    # 1. Fetch pending drifts
    drift_stmt = select(MappingFailureLog).where(MappingFailureLog.applied == False)
    drifts_result = await db.execute(drift_stmt)
    drifts = drifts_result.scalars().all()
    
    # 2. Fetch active mappings
    mapping_stmt = select(ProtocolMapping).where(ProtocolMapping.is_active == True)
    mappings_result = await db.execute(mapping_stmt)
    mappings = mappings_result.scalars().all()
    
    return ReconciliationStatusResponse(
        pending_drifts=[
            DriftStatus(
                id=str(d.id),
                source_protocol=d.source_protocol,
                target_protocol=d.target_protocol,
                source_field=d.source_field,
                suggested_mapping=d.model_suggestion,
                confidence=d.model_confidence,
                error_type=d.error_type,
                payload_excerpt=d.payload_excerpt,
                created_at=d.created_at
            ) for d in drifts
        ],
        active_mappings=[
            MappingStatus(
                source_protocol=m.source_protocol,
                target_protocol=m.target_protocol,
                semantic_equivalents=m.semantic_equivalents,
                version=m.version
            ) for m in mappings
        ]
    )

@router.post("/heal")
async def trigger_healing(db: AsyncSession = Depends(get_session)):
    """
    Triggers the reconciliation repair loop to heal detected drifts.
    """
    try:
        await reconciliation_engine.repair_loop()
        return {"status": "success", "message": "Healing process completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Healing failed: {str(e)}")
