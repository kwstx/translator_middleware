from fastapi import APIRouter, Depends, HTTPException, Response, Request
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
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.core.security import require_scopes, get_current_principal, verify_engram_token
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

router = APIRouter()

from bridge.router import routeTo
# from app.messaging.orchestrator import Orchestrator

# _beta_orchestrator = Orchestrator()

class MiroFishPipeRequest(BaseModel):
    agent_id: str = Field(..., description="The ID of the originating AI agent.")
    protocol: str = Field(..., description="The protocol of the incoming message (e.g., A2A, MCP).")
    payload: Dict[str, Any] = Field(..., description="Wrapper for seed_text and num_agents.")
    swarm_id: str = Field(default="default", description="The target MiroFish swarm simulation identifier.")

    model_config = ConfigDict(extra="forbid")

class MiroFishGodsEyeRequest(BaseModel):
    swarm_id: str = Field(..., description="The target MiroFish swarm simulation identifier.")
    context_objects: List[Dict[str, Any]] = Field(..., description="Live external events (prices, messages) to inject mid-simulation.")

    model_config = ConfigDict(extra="forbid")


class MiroFishPipeResponse(BaseModel):
    status: str
    bridge_id: UUID
    swarm_status: str
    compiled_report: Optional[Dict[str, Any]] = None # Always returns compiled report
    prediction_feedback: Optional[Dict[str, Any]] = None

@router.post(
    "/mirofish/pipe",
    response_model=MiroFishPipeResponse,
    tags=["MiroFish Bridge"],
    summary="Pipe data into MiroFish Swarm (Seed Injection)",
    description="Bridge endpoint to inject seed text and initial agent configurations into a MiroFish swarm.",
)
async def pipe_to_mirofish(
    request: MiroFishPipeRequest,
    db: Session = Depends(get_session),
):
    """
    Pipes message payload into MiroFish swarm simulation.
    Handles 'seed_text' wrapping and 'num_agents' defaulting to 1000.
    """
    import uuid
    
    # Extract seed fields
    seed_text = request.payload.get("seed_text", "")
    num_agents = request.payload.get("num_agents", 1000)
    
    # Simple pass-through translation for now
    try:
        translated_payload = await routeTo(
            target="MCP",
            payload=request.payload,
            source_protocol=request.protocol,
            correlation_id=request.agent_id
        )
    except Exception:
        translated_payload = request.payload # Fallback
        
    return MiroFishPipeResponse(
        status="piped",
        bridge_id=uuid.uuid4(),
        swarm_status="synchronized",
        compiled_report={
            "summary": f"Swarm initialized with {num_agents} agents.",
            "seed_metadata": {"text_length": len(seed_text)},
            "prediction": "Simulation running..."
        },
        prediction_feedback={
            "info": f"Message from {request.agent_id} injected into swarm {request.swarm_id}",
            "translated_payload": translated_payload
        }
    )

@router.post(
    "/mirofish/gods-eye",
    response_model=MiroFishPipeResponse,
    tags=["MiroFish Bridge"],
    summary="God's Eye Injection",
    description="Inject live external events (prices, messages) mid-simulation to influence swarm behavior.",
)
async def mirofish_gods_eye(
    request: MiroFishGodsEyeRequest,
    db: Session = Depends(get_session),
):
    """
    Appends live context objects (market prices or messages) to a running swarm.
    """
    import uuid
    return MiroFishPipeResponse(
        status="injected",
        bridge_id=uuid.uuid4(),
        swarm_status="active_feedback_loop",
        compiled_report={
            "action": "Live context updated",
            "objects_processed": len(request.context_objects)
        }
    )

class RegisterToolRequest(BaseModel):
    name: str = Field(..., description="The name of the tool.")
    description: str = Field(..., description="What the tool does.")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="List of specific actions/functions.")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Input JSON schema.")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Output JSON schema.")
    required_permissions: List[str] = Field(default_factory=list, description="Scopes required to use this tool.")
    version: Optional[str] = Field(None, description="Tool version string.")
    tags: List[str] = Field(default_factory=list, description="Categorization tags.")

class RegisterAgentRequest(BaseModel):
    agent_id: UUID = Field(..., description="Unique UUID for the agent.")
    supported_protocols: List[str] = Field(..., description="Protocols supported by this agent.")
    capabilities: List[str] = Field(default_factory=list, description="Human-readable strings describing features.")
    semantic_tags: List[str] = Field(default_factory=list, description="Ontological tags for discovery.")
    endpoint_url: str = Field(..., description="The base URL where this agent can be reached.")
    tools: List[RegisterToolRequest] = Field(default_factory=list, description="Detailed tool metadata.")

@router.post(
    "/register",
    response_model=AgentRegistry,
    tags=["Registry"],
    summary="Register an agent and its tools",
    description="Registers a new agent along with detailed tool definitions for discovery.",
)
async def register_agent(request: RegisterAgentRequest, db: Session = Depends(get_session)):
    """Registers a new agent and its associated tools."""
    from app.db.models import ToolRegistry
    
    # 1. Create or Update Agent
    stmt = select(AgentRegistry).where(AgentRegistry.agent_id == request.agent_id)
    result = await db.execute(stmt)
    agent = result.scalars().first()
    
    if agent:
        agent.supported_protocols = request.supported_protocols
        agent.capabilities = request.capabilities
        agent.semantic_tags = request.semantic_tags
        agent.endpoint_url = request.endpoint_url
        agent.last_seen = datetime.now(timezone.utc)
        agent.is_active = True
    else:
        agent = AgentRegistry(
            agent_id=request.agent_id,
            supported_protocols=request.supported_protocols,
            capabilities=request.capabilities,
            semantic_tags=request.semantic_tags,
            endpoint_url=request.endpoint_url,
        )
        db.add(agent)
    
    await db.flush() # Ensure agent is in session so we can link tools

    # 2. Register Tools
    for tool_req in request.tools:
        # Check if tool already exists for this agent
        tool_stmt = select(ToolRegistry).where(
            ToolRegistry.agent_id == agent.agent_id,
            ToolRegistry.name == tool_req.name
        )
        tool_result = await db.execute(tool_stmt)
        tool = tool_result.scalars().first()
        
        if tool:
            tool.description = tool_req.description
            tool.actions = tool_req.actions
            tool.input_schema = tool_req.input_schema
            tool.output_schema = tool_req.output_schema
            tool.required_permissions = tool_req.required_permissions
            tool.version = tool_req.version
            tool.tags = tool_req.tags
            tool.updated_at = datetime.now(timezone.utc)
        else:
            tool = ToolRegistry(
                agent_id=agent.agent_id,
                name=tool_req.name,
                description=tool_req.description,
                actions=tool_req.actions,
                input_schema=tool_req.input_schema,
                output_schema=tool_req.output_schema,
                required_permissions=tool_req.required_permissions,
                version=tool_req.version,
                tags=tool_req.tags,
            )
            db.add(tool)

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
        extra="forbid",
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
        extra="forbid",
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
    principal: Dict[str, Any] = require_scopes(["translate:a2a"]),
):
    """Translates a message from source agent protocol to target agent protocol."""
    try:
        # 1. Look up source and target agents to find their protocols
        src_agent_stmt = select(AgentRegistry).where(AgentRegistry.agent_id == UUID(request.source_agent))
        tgt_agent_stmt = select(AgentRegistry).where(AgentRegistry.agent_id == UUID(request.target_agent))
        
        src_res = await db.execute(src_agent_stmt)
        tgt_res = await db.execute(tgt_agent_stmt)
        
        source_agent = src_res.scalars().first()
        target_agent = tgt_res.scalars().first()
        
        if not source_agent or not target_agent:
             raise HTTPException(status_code=404, detail="One or more agents not found in registry.")

        # For multi-protocol agents, we'll pick the first one for now or match against common paths
        source_protocol = source_agent.supported_protocols[0]
        target_protocol = target_agent.supported_protocols[0]

        # 2. Call routeTo with the EAT
        result_payload = await routeTo(
             target=target_protocol,
             payload=request.payload,
             source_protocol=source_protocol,
             correlation_id=f"api-{request.source_agent}",
             eat=principal.get("_raw_token"),
             db=db
        )
        
        record_translation_success("api", source_protocol, target_protocol)
        return TranslateResponse(
            status="completed",
            message=f"Translated message from {request.source_agent} to {request.target_agent}",
            payload=result_payload,
        )
    except Exception as exc:
        record_translation_error("api")
        if isinstance(exc, HTTPException):
             raise
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(exc)}")


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
    principal: Dict[str, Any] = require_scopes(["translate:beta"]),
):
    try:
        result_payload = await routeTo(
            target=request.target_protocol,
            payload=request.payload,
            source_protocol=request.source_protocol,
            correlation_id="beta-translate",
            eat=principal.get("_raw_token"),
            db=db
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
            payload=result_payload,
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
        from app.core.security import create_engram_access_token
        # Playground uses a guest token with broad translator permissions
        guest_eat = create_engram_access_token(
            user_id="playground-guest",
            permissions={"translator": ["*"]}
        )
        
        result_payload = await routeTo(
            target=request.target_protocol,
            payload=request.payload,
            source_protocol=request.source_protocol,
            correlation_id="playground",
            eat=guest_eat,
            db=db
        )
        return BetaTranslateResponse(
            status="success",
            message=(
                f"Translated message from {request.source_protocol} "
                f"to {request.target_protocol}"
            ),
            payload=result_payload,
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
    principal: Dict[str, Any] = require_scopes(["translate:a2a"]),
):
    user_sub = principal.get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Subject missing in token.")
    try:
        user_uuid = UUID(str(user_sub))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user identifier in token.")

    task = Task(
        user_id=user_uuid,
        source_message=request.source_message,
        source_protocol=request.source_protocol,
        target_protocol=request.target_protocol,
        target_agent_id=request.target_agent_id,
        status=TaskStatus.PENDING,
        max_attempts=request.max_attempts,
        eat=principal.get("_raw_token")
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


@router.post(
    "/daemon/start",
    tags=["Daemon"],
    summary="Start background orchestration services",
    description="Launches the background DiscoveryService and TaskWorker using asyncio.create_task.",
)
async def start_daemon(request: Request):
    """
    Triggers the background orchestration loop.
    This starts the periodic agent discovery and task polling workers.
    """
    # 1. Start discovery loop
    await request.app.state.discovery_service.start_periodic_discovery()
    
    # 2. Start worker loop
    await request.app.state.task_worker.start()
    
    return {
        "status": "online",
        "services": ["DiscoveryService", "TaskWorker"],
        "timestamp": datetime.now(timezone.utc)
    }

class DelegateRequest(BaseModel):
    command: str = Field(..., description="The natural language command to delegate.")
    source_agent: str = Field(default="HTTP Client", description="The ID of the originating agent.")

@router.post(
    "/delegate",
    tags=["Delegation"],
    summary="Delegate a subtask via natural language",
    description="Parses a natural language command, detects intent, and routes to a specialized agent.",
)
async def delegate_task(
    request: DelegateRequest,
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    """
    Delegates a task using the DelegationEngine.
    """
    from delegation.engine import delegation_engine
    eat = principal.get("_raw_token")
    if not eat:
        raise HTTPException(status_code=401, detail="Missing Engram Access Token (EAT).")
    try:
        verify_engram_token(eat)
    except Exception as exc:
        raise HTTPException(status_code=403, detail=f"EAT Verification failed: {str(exc)}")
    result = await delegation_engine.delegate_subtask(
        request.command,
        request.source_agent,
        eat=eat,
    )
    return result
