from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Integer, case, func
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.db.session import get_session
from app.db.models import ToolRegistry, ToolExecutionMetadata, ToolRoutingDecision
from app.services.tool_routing import (
    context_aware_prune_tools,
    route_tool_backend_sync,
    fetch_backend_stats,
    available_backends,
    BackendScore,
    RoutingDecision
)

router = APIRouter(prefix="/routing", tags=["Routing"])
logger = structlog.get_logger(__name__)

class RouteTestRequest(BaseModel):
    task_description: str
    force_backend: Optional[str] = None

class BackendScoreModel(BaseModel):
    backend: str
    similarity: float
    performance_score: float
    composite_score: float
    token_cost_est: float
    context_overhead_est: float
    latency_ms: float
    success_rate: float
    preference_score: float

class RouteTestResponse(BaseModel):
    tool_name: str
    selected_backend: str
    confidence_score: float
    predicted_latency_ms: float
    predicted_cost_tokens: float
    reasoning: str
    candidates: List[BackendScoreModel]

@router.post("/test", response_model=RouteTestResponse)
async def test_routing(
    request: RouteTestRequest,
    db: Session = Depends(get_session)
):
    """
    Test the routing engine by simulating a tool selection and backend routing 
    decision for a given task description without executing the tool.
    """
    # 1. Get all tools
    stmt = select(ToolRegistry)
    results = await db.execute(stmt)
    tools = results.scalars().all()
    
    if not tools:
        raise HTTPException(status_code=404, detail="No tools registered in the system.")

    # 2. Prune tools based on context
    # Note: in a real scenarios we'd also pass conversation history
    pruned_tools = context_aware_prune_tools(tools, request.task_description)
    
    if not pruned_tools:
        # Fallback to a few relevant tools if pruning was too strict
        pruned_tools = tools[:5]
        
    best_overall_decision: Optional[RoutingDecision] = None
    best_tool: Optional[ToolRegistry] = None
    
    # 3. Route each pruned tool and find the best tool-backend combination
    for tool in pruned_tools:
        # Fetch execution metadata for the tool
        meta_stmt = select(ToolExecutionMetadata).where(ToolExecutionMetadata.tool_id == tool.id)
        meta_res = await db.execute(meta_stmt)
        metadata = meta_res.scalars().first()
        
        if not metadata:
            continue
            
        backends = available_backends(tool, metadata)
        stats, history = await fetch_backend_stats(db, tool.id, backends, include_history=True)
        
        decision = route_tool_backend_sync(tool, metadata, request.task_description, stats, history)
        
        # Apply manual override if requested
        if request.force_backend:
            target = request.force_backend.upper()
            forced_cand = next((c for c in decision.candidates if c.backend.upper() == target), None)
            if forced_cand:
                decision = RoutingDecision(
                    backend=forced_cand.backend,
                    candidates=decision.candidates,
                    task_description=request.task_description
                )

        # We select the tool-backend pair with the highest composite score
        if decision.candidates:
            current_best_cand = next((c for c in decision.candidates if c.backend == decision.backend), decision.candidates[0])
            
            if best_overall_decision is None:
                best_overall_decision = decision
                best_tool = tool
            else:
                top_best_cand = next((c for c in best_overall_decision.candidates if c.backend == best_overall_decision.backend), best_overall_decision.candidates[0])
                if current_best_cand.composite_score > top_best_cand.composite_score:
                    best_overall_decision = decision
                    best_tool = tool

    if not best_overall_decision or not best_tool:
        raise HTTPException(status_code=500, detail="Routing engine could not determine a suitable tool.")

    best_cand = next((c for c in best_overall_decision.candidates if c.backend == best_overall_decision.backend), best_overall_decision.candidates[0])
    
    # Generate reasoning
    reasoning = (
        f"Selected '{best_tool.name}' via {best_overall_decision.backend} backend. "
        f"Semantic similarity: {best_cand.similarity:.2f}. "
    )
    if best_cand.success_rate > 0.95:
        reasoning += "Prioritized stability over latency. "
    elif best_cand.latency_ms < 300:
        reasoning += "Optimized for sub-second latency. "
    
    if request.force_backend:
        reasoning += f" (Manual override: forced {request.force_backend})"

    return RouteTestResponse(
        tool_name=best_tool.name,
        selected_backend=best_overall_decision.backend,
        confidence_score=best_cand.composite_score,
        predicted_latency_ms=best_cand.latency_ms,
        predicted_cost_tokens=best_cand.token_cost_est,
        reasoning=reasoning,
        candidates=[
            BackendScoreModel(
                backend=c.backend,
                similarity=c.similarity,
                performance_score=c.performance_score,
                composite_score=c.composite_score,
                token_cost_est=c.token_cost_est,
                context_overhead_est=c.context_overhead_est,
                latency_ms=c.latency_ms,
                success_rate=c.success_rate,
                preference_score=c.preference_score
            ) for c in best_overall_decision.candidates
        ]
    )

class ToolStats(BaseModel):
    tool_name: str
    backend: str
    avg_latency_ms: float
    success_rate: float
    avg_cost_tokens: float
    samples: int

@router.get("/list", response_model=List[ToolStats])
async def list_tool_stats(
    db: Session = Depends(get_session)
):
    """
    Returns a list of tools with aggregated historical performance metrics.
    """
    success_case = case(
        (ToolRoutingDecision.success == True, 1),
        else_=0,
    )
    
    stmt = (
        select(
            ToolRegistry.name,
            ToolRoutingDecision.backend_selected,
            func.avg(ToolRoutingDecision.latency_ms).label("avg_latency"),
            func.avg(success_case.cast(Integer)).label("avg_success"),
            func.avg(ToolRoutingDecision.token_cost_actual).label("avg_cost"),
            func.count(ToolRoutingDecision.id).label("samples")
        )
        .join(ToolRoutingDecision, ToolRegistry.id == ToolRoutingDecision.tool_id)
        .group_by(ToolRegistry.name, ToolRoutingDecision.backend_selected)
        .order_by(func.avg(ToolRoutingDecision.latency_ms))
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    stats_list = []
    for row in rows:
        name, backend, latency, success, cost, samples = row
        stats_list.append(ToolStats(
            tool_name=name,
            backend=backend,
            avg_latency_ms=float(latency or 0.0),
            success_rate=float(success or 0.0),
            avg_cost_tokens=float(cost or 0.0),
            samples=int(samples or 0)
        ))
    
    return stats_list
