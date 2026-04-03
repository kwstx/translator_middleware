from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import AgentRegistry, ProtocolMapping
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.discovery import DiscoveryService
from app.core.security import require_scopes

router = APIRouter(prefix="/discovery", tags=["Discovery"], dependencies=[require_scopes([])])


@router.get("/agents", response_model=List[AgentRegistry])
async def list_agents(db: Session = Depends(get_session)):
    """
    List all registered agents.
    """
    stmt = select(AgentRegistry)
    results = await db.execute(stmt)
    agents = results.scalars().all()
    return agents


class AgentDiscoveryRequest(BaseModel):
    protocols: List[str] = Field(
        ..., description="List of protocols supported by the agent"
    )
    semantic_tags: List[str] = Field(
        ..., description="Semantic capabilities or tags to match"
    )


class CollaboratorResult(BaseModel):
    """Rich response showing an agent and its compatibility details."""

    agent_id: str
    endpoint_url: str
    supported_protocols: List[str]
    is_active: bool
    compatibility_score: float = Field(
        ..., description="Score computed as (shared + mappable) / total protocols"
    )
    shared_protocols: List[str] = Field(
        default=[], description="Protocols directly shared between source and target"
    )
    mappable_protocols: List[str] = Field(
        default=[],
        description="Protocols reachable via translation mappings",
    )


@router.post("/", response_model=List[AgentRegistry])
async def discover_agents(
    request: AgentDiscoveryRequest,
    db: Session = Depends(get_session),
):
    """
    Discovers agents that either support the requested protocols directly
    or can be reached via protocol translation, filtered by semantic tags.
    """
    # 1. Determine compatible protocols (direct + translatable)
    requested_protocols = request.protocols

    # Query for protocol mappings starting from source protocols
    mapping_stmt = select(ProtocolMapping).where(
        ProtocolMapping.source_protocol.in_(requested_protocols)
    )
    mapping_results = await db.execute(mapping_stmt)
    mappings = mapping_results.scalars().all()

    # Target protocols we can translate into
    translatable_to = {m.target_protocol for m in mappings}
    eligible_protocols = set(requested_protocols) | translatable_to

    # 2. Search AgentRegistry for matching agents
    stmt = select(AgentRegistry).where(
        AgentRegistry.supported_protocols.overlap(list(eligible_protocols))
    )

    # 3. Apply semantic tag filtering
    if request.semantic_tags:
        stmt = stmt.where(
            AgentRegistry.semantic_tags.overlap(request.semantic_tags)
        )

    results = await db.execute(stmt)
    agents = results.scalars().all()

    return agents


@router.get("/collaborators", response_model=List[CollaboratorResult])
async def get_collaborators(
    protocols: str = Query(
        ...,
        description="Comma-separated list of protocols the requesting agent supports",
    ),
    min_score: float = Query(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum compatibility score threshold (0.0 – 1.0)",
    ),
    db: Session = Depends(get_session),
):
    """
    Finds collaborative agents based on the compatibility score formula:

        score = (shared_protocols + mappable_protocols) / total_protocols

    Only agents with score >= min_score are returned, sorted by score descending.
    """
    protocol_list = [p.strip() for p in protocols.split(",") if p.strip()]

    results = await DiscoveryService.find_collaborators(
        session=db,
        source_protocols=protocol_list,
        min_score=min_score,
    )

    # Map the rich dict results into the response model
    collaborator_responses = []
    for entry in results:
        agent = entry["agent"]
        collaborator_responses.append(
            CollaboratorResult(
                agent_id=str(agent.agent_id),
                endpoint_url=agent.endpoint_url,
                supported_protocols=agent.supported_protocols,
                is_active=agent.is_active,
                compatibility_score=entry["compatibility_score"],
                shared_protocols=entry["shared_protocols"],
                mappable_protocols=entry["mappable_protocols"],
            )
        )

    return collaborator_responses
