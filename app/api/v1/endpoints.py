from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import (
    AgentRegistry,
    SemanticOntology,
    Task,
    TaskStatus,
    AgentMessage,
    AgentMessageStatus,
)
from app.semantic.ontology_manager import ontology_manager
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.core.security import require_scopes
from app.core.metrics import record_translation_error, record_translation_success
from app.core.config import settings
from app.services.queue import lease_agent_message
from app.messaging.orchestrator import Orchestrator
from app.services.mapping_failures import (
    extract_fields,
    extract_payload_excerpt,
    log_mapping_failure,
    apply_ml_suggestion,
)

router = APIRouter(dependencies=[require_scopes([])])
_beta_orchestrator = Orchestrator()

class MiroFishPipeRequest(BaseModel):
    agent_id: str = Field(..., description="The ID of the originating AI agent.")
    protocol: str = Field(..., description="The protocol of the incoming message (e.g., A2A, MCP).")
    payload: Dict[str, Any] = Field(..., description="The message or data to pipe into the swarm.")
    swarm_id: str = Field(default="default", description="The target MiroFish swarm simulation identifier.")

class MiroFishPipeResponse(BaseModel):
    status: str
    bridge_id: UUID
    swarm_status: str
    prediction_feedback: Optional[Dict[str, Any]] = None

@router.post(
    "/mirofish/pipe",
    response_model=MiroFishPipeResponse,
    tags=["MiroFish Bridge"],
    summary="Pipe data into MiroFish Swarm",
    description="Bridge endpoint to inject inter-agent messages and live data into a MiroFish swarm.",
)
async def pipe_to_mirofish(
    request: MiroFishPipeRequest,
    db: Session = Depends(get_session),
):
    """
    Pipes message payload into MiroFish swarm simulation.
    This is a 'one-line router' for external agents to sync with the swarm.
    """
    # Logic: 
    # 1. Translate payload to 'MCP' (internal swarm protocol) if needed
    # 2. Inject into 'God's-eye variables' or seed text (mocked for now)
    # 3. Return a bridge ID for tracking
    import uuid
    
    # Simple pass-through translation for now
    try:
        translated_result = _beta_orchestrator.handoff(
            request.payload, request.protocol, "MCP"
        )
        translated_payload = translated_result.translated_message
    except Exception:
        translated_payload = request.payload # Fallback
        
    return MiroFishPipeResponse(
        status="piped",
        bridge_id=uuid.uuid4(),
        swarm_status="synchronized",
        prediction_feedback={
            "info": f"Message from {request.agent_id} injected into swarm {request.swarm_id}",
            "translated_payload": translated_payload
        }
    )

@router.post(
    "/register",
    response_model=AgentRegistry,
    tags=["Registry"],
    summary="Register an agent",
    description="Registers a new agent with its supported protocols and capabilities.",
)
async def register_agent(agent: AgentRegistry, db: Session = Depends(get_session)):
    """Registers a new agent with its supported protocols and capabilities."""
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent

@router.get(
    "/discover",
    response_model=List[AgentRegistry],
    tags=["Registry"],
    summary="Discover registered agents",
    description="Discovers agents capable of handling specific protocols or tasks.",
)
async def discover_agents(protocol: str = None, capability: str = None, db: Session = Depends(get_session)):
    """Discovers agents capable of handling specific protocols or tasks."""
    statement = select(AgentRegistry)
    if protocol:
        statement = statement.where(AgentRegistry.supported_protocols.contains([protocol]))
    # Capability filtering can be added here with more logic
    results = await db.execute(statement)
    return results.scalars().all()

class TranslateRequest(BaseModel):
    source_agent: str = Field(
        ...,
        description="Agent identifier or registry ID for the source agent.",
        examples=["agent-a"],
    )
    target_agent: str = Field(
        ...,
        description="Agent identifier or registry ID for the target agent.",
        examples=["agent-b"],
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Protocol-specific payload to translate.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source_agent": "agent-a",
                    "target_agent": "agent-b",
                    "payload": {
                        "intent": "schedule_meeting",
                        "participants": ["alice@example.com", "bob@example.com"],
                        "window": {"start": "2026-03-12T09:00:00Z", "end": "2026-03-12T11:00:00Z"},
                        "timezone": "UTC",
                    },
                }
            ]
        }
    )


class TranslateResponse(BaseModel):
    status: str = Field(..., description="Translation lifecycle status.")
    message: str = Field(..., description="Human-readable status message.")
    payload: Dict[str, Any] = Field(..., description="Translated or queued payload.")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "pending",
                    "message": "Translating message from agent-a to agent-b",
                    "payload": {
                        "intent": "schedule_meeting",
                        "participants": ["alice@example.com", "bob@example.com"],
                        "time_range": {
                            "from": "2026-03-12T09:00:00Z",
                            "to": "2026-03-12T11:00:00Z",
                        },
                    },
                }
            ]
        }
    )

class BetaTranslateRequest(BaseModel):
    source_protocol: str = Field(..., description="Source protocol identifier.")
    target_protocol: str = Field(..., description="Target protocol identifier.")
    payload: Dict[str, Any] = Field(..., description="Protocol-specific payload.")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source_protocol": "A2A",
                    "target_protocol": "MCP",
                    "payload": {
                        "payload": {
                            "intent": "dispatch",
                            "delivery_window": {
                                "start": "2026-03-12T09:00:00Z",
                                "end": "2026-03-12T11:00:00Z",
                            },
                        }
                    },
                }
            ]
        }
    )


class MappingSuggestion(BaseModel):
    source_field: str
    suggestion: str | None = None
    confidence: float | None = None
    applied: bool = False


class BetaTranslateResponse(TranslateResponse):
    mapping_suggestions: List[MappingSuggestion] = Field(
        default_factory=list,
        description="ML-generated mapping suggestions captured during failures.",
    )


@router.post(
    "/translate",
    response_model=TranslateResponse,
    tags=["Translation"],
    summary="Translate a message between agent protocols",
    description="Translates a message from a source agent protocol to a target agent protocol.",
)
async def translate_message(
    request: TranslateRequest,
    db: Session = Depends(get_session),
    _principal: Dict[str, Any] = require_scopes(["translate:a2a"]),
):
    """Translates a message from source agent protocol to target agent protocol."""
    # 1. Look up source and target agents
    # 2. Identify protocol mapping rules
    # 3. Apply semantic mapping using ontology_manager
    # 4. Return translated payload or queue it for handoff
    # Placeholder for translation logic
    try:
        response = {
            "status": "pending",
            "message": f"Translating message from {request.source_agent} to {request.target_agent}",
            "payload": request.payload,
        }
        record_translation_success("api")
        return response
    except Exception:
        record_translation_error("api")
        raise


@router.post(
    "/beta/translate",
    response_model=BetaTranslateResponse,
    tags=["Beta"],
    summary="Beta translate endpoint for enterprise users",
    description="Enterprise beta endpoint that logs failed mappings and attaches ML suggestions.",
)
async def beta_translate_message(
    request: BetaTranslateRequest,
    db: Session = Depends(get_session),
    _principal: Dict[str, Any] = require_scopes(["translate:beta"]),
):
    try:
        result = _beta_orchestrator.handoff(
            request.payload, request.source_protocol, request.target_protocol
        )
        record_translation_success(
            "beta", request.source_protocol.upper(), request.target_protocol.upper()
        )
        return BetaTranslateResponse(
            status="success",
            message=(
                f"Translated message from {request.source_protocol} "
                f"to {request.target_protocol}"
            ),
            payload=result.translated_message,
            mapping_suggestions=[],
        )
    except Exception as exc:
        fields = extract_fields(request.payload, settings.MAPPING_FAILURE_MAX_FIELDS)
        payload_excerpt = extract_payload_excerpt(
            request.payload, settings.MAPPING_FAILURE_PAYLOAD_MAX_KEYS
        )
        suggestions: List[MappingSuggestion] = []
        logs = []
        for field in fields:
            entry = await log_mapping_failure(
                db,
                source_protocol=request.source_protocol,
                target_protocol=request.target_protocol,
                source_field=field,
                payload_excerpt=payload_excerpt,
                error_type=type(exc).__name__,
            )
            logs.append(entry)

        for entry in logs:
            await apply_ml_suggestion(db, entry)
            suggestions.append(
                MappingSuggestion(
                    source_field=entry.source_field,
                    suggestion=entry.model_suggestion,
                    confidence=entry.model_confidence,
                    applied=entry.applied,
                )
            )
        await db.commit()
        record_translation_error(
            "beta", request.source_protocol.upper(), request.target_protocol.upper()
        )
        raise HTTPException(
            status_code=422,
            detail="Translation failed; mapping failures logged.",
        ) from exc


@router.post(
    "/beta/playground/translate",
    response_model=BetaTranslateResponse,
    tags=["Beta", "Playground"],
    summary="Playground endpoint (no JWT required)",
    description="Public sandbox endpoint for the Web Playground to translate messages instantly.",
)
async def playground_translate_message(
    request: BetaTranslateRequest,
    db: Session = Depends(get_session),
):
    try:
        result = _beta_orchestrator.handoff(
            request.payload, request.source_protocol, request.target_protocol
        )
        return BetaTranslateResponse(
            status="success",
            message=(
                f"Translated message from {request.source_protocol} "
                f"to {request.target_protocol}"
            ),
            payload=result.translated_message,
            mapping_suggestions=[],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Playground Translation failed: {str(exc)}",
        )


class TaskEnqueueRequest(BaseModel):
    source_message: Dict[str, Any] = Field(
        ..., description="Message payload to be translated."
    )
    source_protocol: str = Field(
        ..., description="Protocol used by the source agent."
    )
    target_protocol: str = Field(
        ..., description="Protocol expected by the target agent."
    )
    target_agent_id: UUID = Field(
        ..., description="Registry ID of the target agent."
    )
    max_attempts: int = Field(default_factory=lambda: settings.TASK_MAX_ATTEMPTS)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source_message": {
                        "intent": "summarize",
                        "content": "Summarize the attached report.",
                    },
                    "source_protocol": "a2a",
                    "target_protocol": "mcp",
                    "target_agent_id": "9b6c2c9b-7c8e-4f5b-9f3e-2a9cfa45c3b1",
                    "max_attempts": 5,
                }
            ]
        }
    )


class TaskEnqueueResponse(BaseModel):
    task_id: UUID
    status: TaskStatus


class AgentMessageLeaseResponse(BaseModel):
    message_id: UUID
    task_id: UUID
    payload: Dict[str, Any]
    leased_until: datetime


@router.post(
    "/queue/enqueue",
    response_model=TaskEnqueueResponse,
    tags=["Queue"],
    summary="Enqueue a translation task",
    description="Queues a translation task for asynchronous processing.",
)
async def enqueue_task(
    request: TaskEnqueueRequest,
    db: Session = Depends(get_session),
):
    task = Task(
        source_message=request.source_message,
        source_protocol=request.source_protocol,
        target_protocol=request.target_protocol,
        target_agent_id=request.target_agent_id,
        status=TaskStatus.PENDING,
        max_attempts=request.max_attempts,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return TaskEnqueueResponse(task_id=task.id, status=task.status)


@router.post(
    "/agents/{agent_id}/messages/poll",
    response_model=AgentMessageLeaseResponse,
    tags=["Queue"],
    summary="Poll for agent messages",
    description="Leases the next queued message for the specified agent.",
)
async def poll_agent_messages(
    agent_id: UUID,
    lease_seconds: int = settings.AGENT_MESSAGE_LEASE_SECONDS,
    db: Session = Depends(get_session),
):
    message = await lease_agent_message(
        db,
        agent_id=agent_id,
        lease_owner=f"agent-{agent_id}",
        lease_seconds=lease_seconds,
    )
    if not message:
        return Response(status_code=204)
    return AgentMessageLeaseResponse(
        message_id=message.id,
        task_id=message.task_id,
        payload=message.payload,
        leased_until=message.leased_until,
    )


@router.post(
    "/agents/messages/{message_id}/ack",
    tags=["Queue"],
    summary="Acknowledge an agent message",
    description="Acknowledges a leased agent message and clears its lease.",
)
async def ack_agent_message(
    message_id: UUID,
    db: Session = Depends(get_session),
):
    result = await db.execute(
        select(AgentMessage).where(AgentMessage.id == message_id)
    )
    message = result.scalars().first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")

    if message.status == AgentMessageStatus.ACKED:
        return {"status": "acked", "message_id": str(message.id)}

    message.status = AgentMessageStatus.ACKED
    message.acked_at = datetime.now(timezone.utc)
    message.lease_owner = None
    message.leased_until = None
    message.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "acked", "message_id": str(message.id)}

@router.post(
    "/ontology/upload",
    tags=["Ontology"],
    summary="Upload an RDF ontology",
    description="Uploads an RDF/XML ontology and loads it into the in-memory graph.",
)
async def upload_ontology(name: str, rdf_xml: str, db: Session = Depends(get_session)):
    """Uploads an RDF ontology for semantic mapping."""
    ontology = SemanticOntology(name=name, namespace="http://local.ontology/", rdf_content=rdf_xml)
    db.add(ontology)
    await db.commit()
    await db.refresh(ontology)
    
    # Load into memory-based RDFlib graph
    ontology_manager.load_ontology(rdf_xml, format="xml")
    return {"status": "success", "id": str(ontology.id)}
