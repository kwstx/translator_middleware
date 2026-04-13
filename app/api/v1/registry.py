import uuid
import time
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select
import structlog
from app.db.session import get_session
from app.core.security import get_current_principal, verify_engram_token
from app.core.semantic_auth import SemanticAuthorizationService
import subprocess
from app.db.models import ToolRegistry, ToolExecutionMetadata
from app.services.registry_service import RegistryService
from app.schemas.tool import ManualToolCreate
from app.services.semantic_trace import SemanticTrace, record_trace
from app.services.tool_routing import (
    available_backends,
    estimate_backend_stats,
    estimate_tokens,
    fetch_backend_stats,
    log_routing_decision,
    route_tool_backend_sync,
    finalize_routing_decision,
    RoutingDecision,
    context_aware_prune_tools,
    MCP_BACKEND,
    HTTP_BACKEND,
    CLI_BACKEND,
)

router = APIRouter(prefix="/registry", tags=["Registry"])
logger = structlog.get_logger(__name__)

# --- Ingestion Endpoints ---

@router.post("/ingest/openapi", status_code=status.HTTP_201_CREATED)
async def ingest_openapi(
    url_or_path: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Ingests an OpenAPI spec and registers its tools.
    """
    service = RegistryService(db)
    agent_uuid = uuid.UUID(agent_id)
    user_id_str = principal.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    
    tool = await service.ingest_openapi(url_or_path, agent_uuid, user_id=user_uuid)
    return tool

@router.post("/ingest/cli", status_code=status.HTTP_201_CREATED)
async def ingest_cli(
    command: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Ingests a CLI tool by parsing its --help output.
    """
    service = RegistryService(db)
    agent_uuid = uuid.UUID(agent_id)
    user_id_str = principal.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    
    tool = await service.ingest_cli_help(command, agent_uuid, user_id=user_uuid)
    return tool


@router.post("/ingest/docs", status_code=status.HTTP_201_CREATED)
async def ingest_docs(
    docs_text: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Ingests tools from partial documentation text using LLM extraction.
    """
    service = RegistryService(db)
    agent_uuid = uuid.UUID(agent_id)
    user_id_str = principal.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    
    tool = await service.extract_from_docs(docs_text, agent_uuid, user_id=user_uuid)
    return tool

@router.post("/manual", status_code=status.HTTP_201_CREATED)
async def register_manual_tool(
    data: ManualToolCreate,
    agent_id: uuid.UUID = Body(..., embed=True),
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Manually registers a tool with its specific HTTP details and parameters.
    """
    service = RegistryService(db)
    user_id_str = principal.get("sub")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None
    
    tool = await service.create_manual_tool(data, agent_id, user_id=user_uuid)
    return tool

from sqlalchemy.orm import selectinload

# --- Response Models ---

class ToolExecutionMetadataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    execution_type: str
    exec_params: Dict[str, Any]
    cli_wrapper: Optional[str] = None
    docker_image: Optional[str] = None
    docker_config: Dict[str, Any] = {}
    auth_config: Dict[str, Any] = {}

class ToolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    description: str
    version: Optional[str] = None
    tags: List[str] = []
    actions: List[Dict[str, Any]] = []
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    execution_metadata: Optional[ToolExecutionMetadataRead] = None

@router.get("/tools", response_model=List[ToolRead])
async def list_tools(
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    List all registered tools including their execution backend metadata.
    """
    try:
        user_id = principal.get("sub")
        stmt = select(ToolRegistry)
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                stmt = stmt.where(ToolRegistry.user_id == user_uuid)
            except (ValueError, TypeError):
                # If current token has a non-UUID identity (like an old email-based sub),
                # we skip filtering to avoid 500, though this user likely won't see any private tools.
                logger.warning("Non-UUID identity found in token", user_id=user_id)
                pass
        
        stmt = stmt.options(selectinload(ToolRegistry.execution_metadata))
        results = await db.execute(stmt)
        tools = results.scalars().all()
        logger.info("Found tools", count=len(tools), user_id=user_id)
        return tools
    except Exception as e:
        logger.exception("Failed to list tools", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal database error when listing tools: {str(e)}"
        )


# --- Scope Management Endpoints ---

class ScopeActivateRequest(BaseModel):
    scope_id: str
    tools: List[str]
    corrected_schemas: Dict[str, Any] = {}
    routing_decisions: Dict[str, str] = {}
    metadata: Dict[str, Any] = {}


class ScopeValidateRequest(BaseModel):
    tools: List[str]


class NamedScopeRequest(BaseModel):
    name: str
    tools: List[str]


class ToolValidationResult(BaseModel):
    tool_id: str
    drift: bool
    corrected_schema: Optional[Dict[str, Any]] = None
    best_backend: str


class ScopeValidationResult(BaseModel):
    results: Dict[str, ToolValidationResult]

@router.post("/scope/activate", status_code=status.HTTP_201_CREATED)
async def activate_scope(
    request: ScopeActivateRequest,
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Registers a narrow tool scope for a specific conversation turn/step.
    Stored in Redis for fast lookup during MCP discovery.
    """
    from app.core.redis_client import get_redis_client
    redis = get_redis_client()
    if not redis:
        logger.warning("Scope activation failed: Redis unavailable")
        # We don't throw 500 here to allow fallback to ambient discovery if Redis is down,
        # but in a hardened environment we might want to fail closed.
        return {"status": "error", "message": "Persistence unavailable"}

    user_id = principal.get("sub")
    key = f"engram:scope:active:{user_id}:{request.scope_id}"
    
    scope_data = {
        "tools": request.tools,
        "corrected_schemas": request.corrected_schemas,
        "routing_decisions": request.routing_decisions,
        "metadata": request.metadata,
        "activated_at": time.time()
    }
    
    # TTL for scopes: 30 minutes for a conversation turn seems reasonable
    redis.setex(key, 1800, json.dumps(scope_data))
    logger.info("Scope activated", scope_id=request.scope_id, user_id=user_id, tool_count=len(request.tools))
    
    return {"status": "ok", "scope_id": request.scope_id}


@router.post("/scope", status_code=status.HTTP_201_CREATED)
async def create_named_scope(
    request: NamedScopeRequest,
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Registers a named scope template for future activation.
    Stored in Redis as a template.
    """
    from app.core.redis_client import get_redis_client
    redis = get_redis_client()
    if not redis:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    user_id = principal.get("sub")
    key = f"engram:scope:template:{user_id}:{request.name}"
    
    redis.set(key, json.dumps(request.tools))
    logger.info("Named scope created", name=request.name, user_id=user_id, tool_count=len(request.tools))
    
    return {"status": "ok", "name": request.name}


@router.get("/scope/{name}", response_model=List[str])
async def get_named_scope(
    name: str,
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Retrieves the tools associated with a named scope template.
    """
    from app.core.redis_client import get_redis_client
    redis = get_redis_client()
    if not redis:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    user_id = principal.get("sub")
    key = f"engram:scope:template:{user_id}:{name}"
    
    tools_raw = redis.get(key)
    if not tools_raw:
        # Fallback: check if 'all' is requested
        if name == "all":
            from sqlmodel import select
            from app.db.models import ToolRegistry
            from app.db.session import get_session
            # This is a bit complex in a GET route without a Session dependency, 
            # but for our current architecture, named scopes are the hero.
            raise HTTPException(status_code=404, detail="Global 'all' scope must be explicitly managed or fallback to discovery.")
            
        raise HTTPException(status_code=404, detail=f"Scope template '{name}' not found")
        
    return json.loads(tools_raw)


@router.post("/scope/validate", response_model=ScopeValidationResult)
async def validate_scope_tools(
    request: ScopeValidateRequest,
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Batch validates tools in a scope for drift and pre-calculates the best performance-based backend.
    """
    from app.reconciliation.engine import reconciliation_engine
    
    results = {}
    for tool_name in request.tools:
        # 1. Check for drift
        stmt = select(ToolRegistry).where(ToolRegistry.name == tool_name)
        user_id = principal.get("sub")
        if user_id:
            try:
                stmt = stmt.where(ToolRegistry.user_id == uuid.UUID(user_id))
            except ValueError:
                pass
        
        stmt = stmt.options(selectinload(ToolRegistry.execution_metadata))
        tool_res = await db.execute(stmt)
        tool = tool_res.scalars().first()
        
        if not tool:
            continue

        corrected = await reconciliation_engine.validate_tool_drift(tool_name, tool.input_schema or {})
        
        # 2. Determine best backend based on graph performance (ignoring task similarity)
        best_backend = CLI_BACKEND # Default
        metadata = tool.execution_metadata
        if metadata:
            backends = available_backends(tool, metadata)
            # Use fetch_backend_stats (async) and then route_tool_backend_sync
            stats, history = await fetch_backend_stats(db, tool.id, backends, include_history=True)
            stats = {
                backend: estimate_backend_stats(tool, metadata, backend, "", stats.get(backend))
                for backend in backends
            }
            decision = route_tool_backend_sync(tool, metadata, "", stats, history_by_backend=history)
            best_backend = decision.backend

        results[tool_name] = ToolValidationResult(
            tool_id=str(tool.id),
            drift=bool(corrected),
            corrected_schema=corrected,
            best_backend=best_backend
        )
    
    return ScopeValidationResult(results=results)


# --- MCP Native Server Implementation (JSON-RPC over HTTP) ---

@router.post("/mcp/call", response_model=Dict[str, Any])
async def call_mcp_tool(
    request: Dict[str, Any] = Body(...),
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Implement JSON-RPC 2.0 to call a registered tool.
    Discovery + Execution for agents.
    """
    # JSON-RPC Handling
    method = request.get("method")
    params = request.get("params", {})
    jsonrpc_id = request.get("id")

    if method == "mcp.list_tools":
        task_intent = params.get("task_intent", "")
        conversation_history = params.get("conversation_history", [])
        scope_id = params.get("scope_id") or params.get("step_id")
        user_id = principal.get("sub")
        
        active_scope = None
        if scope_id and user_id:
            from app.core.redis_client import get_redis_client
            redis = get_redis_client()
            if redis:
                scope_key = f"engram:scope:active:{user_id}:{scope_id}"
                cached_scope = redis.get(scope_key)
                if cached_scope:
                    active_scope = json.loads(cached_scope)
                    logger.info("Found active scope for turn", scope_id=scope_id, user_id=user_id)

        stmt = select(ToolRegistry)
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                stmt = stmt.where(ToolRegistry.user_id == user_uuid)
            except (ValueError, TypeError):
                pass
            
        results = await db.execute(stmt)
        raw_tools = results.scalars().all()
        
        # If an active scope is found, we ONLY return tools in that scope
        if active_scope:
            scope_tools = set(active_scope.get("tools", []))
            corrected_schemas = active_scope.get("corrected_schemas", {})
            
            pruned_tools = [t for t in raw_tools if t.name in scope_tools]
            
            result = []
            for t in pruned_tools:
                # Use corrected schema if available from the pre-validation step
                schema = corrected_schemas.get(t.name) or t.input_schema or {}
                result.append({
                    "id": str(t.id),
                    "name": t.name,
                    "description": t.description,
                    "actions": t.actions or [],
                    "input_schema": schema
                })
            
            logger.info("Serving scoped discovery", scope_id=scope_id, served_count=len(result))
            return {"jsonrpc": "2.0", "id": jsonrpc_id, "result": {"tools": result}}

        # Fallback to ambient discovery if no specific scope is active
        pruned_tools = context_aware_prune_tools(raw_tools, task_intent, conversation_history)
        
        result = [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "actions": t.actions or [],
                "input_schema": t.input_schema or {}
            }
            for t in pruned_tools
        ]
        return {"jsonrpc": "2.0", "id": jsonrpc_id, "result": {"tools": result}}

    if method == "mcp.call_tool":
        tool_id = params.get("tool_id")
        action_name = params.get("action")
        arguments = params.get("arguments", {})
        task_description = params.get("task_description") or params.get("task")

        tool = await db.get(ToolRegistry, uuid.UUID(tool_id))
        if not tool:
            return {"jsonrpc": "2.0", "id": jsonrpc_id, "error": {"code": -32601, "message": "Tool not found"}}

        # Determine execution path
        metadata = tool.execution_metadata
        if metadata:
            # Check for cached routing decision in active scope
            scope_id = params.get("scope_id") or params.get("step_id")
            user_id = principal.get("sub")
            backend_override = None
            
            if scope_id and user_id:
                from app.core.redis_client import get_redis_client
                redis = get_redis_client()
                if redis:
                    scope_key = f"engram:scope:active:{user_id}:{scope_id}"
                    cached_scope_raw = redis.get(scope_key)
                    if cached_scope_raw:
                        active_scope = json.loads(cached_scope_raw)
                        
                        # Enforce Scope Authorization: The model proposes, the code disposes.
                        scope_tools = active_scope.get("tools", [])
                        if tool.name not in scope_tools and str(tool.id) not in scope_tools:
                            logger.warning("Scope violation: blocked tool call", tool=tool.name, scope_id=scope_id)
                            return {
                                "jsonrpc": "2.0", 
                                "id": jsonrpc_id, 
                                "error": {
                                    "code": -32003, 
                                    "message": f"Scope Violation: Tool '{tool.name}' is not authorized for the current turn."
                                }
                            }

                        backend_override = active_scope.get("routing_decisions", {}).get(tool.name)
                        if backend_override:
                            logger.info("Using cached routing decision from scope", 
                                        tool=tool.name, backend=backend_override, scope_id=scope_id)

            if backend_override:
                # Bypass routing engine
                selected_backend = backend_override
                # We still create a mock decision for the logging/trace infrastructure
                decision = RoutingDecision(
                    backend=selected_backend,
                    candidates=[],
                    task_description=task_description or "Scoped lookup"
                )
                # Skip log_routing_decision if we want 'almost zero overhead', 
                # but we'll need a record ID for the finalize call.
                # To truly minimize overhead, we could make finalize optional if record is missing.
                decision_record = None 
            else:
                task_description = _infer_task_description(tool, action_name, arguments, task_description)
                backends = available_backends(tool, metadata)
                stats, history = await fetch_backend_stats(db, tool.id, backends, include_history=True)
                stats = {
                    backend: estimate_backend_stats(tool, metadata, backend, task_description, stats.get(backend))
                    for backend in backends
                }
                decision = route_tool_backend_sync(tool, metadata, task_description, stats, history_by_backend=history)
                decision_record = await log_routing_decision(db, tool.id, action_name, decision)
                selected_backend = decision.backend

            import structlog
            structlog.contextvars.bind_contextvars(
                routing_choice=selected_backend,
                backend_used=selected_backend,
                ontological_interpretations=f"Mapped '{action_name or 'default'}' to ontology '{tool.name}'",
                reconciliation_steps="schema_compression_and_validation"
            )
            logger.info(
                "Execution Path Triggered",
                tool_id=str(tool.id),
                routing_choice=selected_backend,
                backend_used=selected_backend,
                ontological_interpretations=f"Mapped '{action_name or 'default'}' to ontology '{tool.name}'",
                reconciliation_steps="schema_compression_and_validation",
                execution_type=selected_backend
            )

            start = time.perf_counter()
            error_message = None
            try:
                if selected_backend == CLI_BACKEND:
                    result = await run_cli_execution(tool, metadata, action_name, arguments, principal)
                elif selected_backend in {MCP_BACKEND, HTTP_BACKEND}:
                    result = await run_http_execution(tool, metadata, action_name, arguments, principal)
                else:
                    result = await run_http_execution(tool, metadata, action_name, arguments, principal)
            except Exception as exc:
                error_message = str(exc)
                raise
            finally:
                latency_ms = (time.perf_counter() - start) * 1000.0
                token_cost_actual = _estimate_result_tokens(result if "result" in locals() else {"error": error_message})
                success = False
                if "result" in locals() and isinstance(result, dict):
                    if "error" in result:
                        success = False
                        error_message = error_message or result.get("error", {}).get("message")
                    elif "result" in result:
                        success = True
                
                if decision_record:
                    await finalize_routing_decision(
                        db,
                        decision_record.id,
                        success=success,
                        latency_ms=latency_ms,
                        token_cost_actual=token_cost_actual,
                        error=error_message,
                    )
                
                # Record semantic trace for observability
                best = decision.candidates[0] if decision.candidates else None
                record_trace(SemanticTrace(
                    tool_name=tool.name,
                    action=action_name or "",
                    routing_choice=selected_backend,
                    backend_used=selected_backend,
                    similarity_score=best.similarity if best else 0.0,
                    composite_score=best.composite_score if best else 0.0,
                    token_cost_est=best.token_cost_est if best else 0.0,
                    context_overhead_est=best.context_overhead_est if best else 0.0,
                    reconciliation_steps=["authz_enforcement", "schema_compression", "backend_routing"],
                    ontological_interpretation=(
                        f"{selected_backend} chosen for "
                        f"{'token efficiency' if selected_backend == CLI_BACKEND else 'schema richness'}; "
                        f"tool '{tool.name}' action '{action_name or 'default'}'"
                    ),
                    success=success,
                    latency_ms=latency_ms,
                    error=error_message,
                ))
            return result

        return {"jsonrpc": "2.0", "id": jsonrpc_id, "error": {"code": -32603, "message": "Execution type not supported yet"}}

    return {"jsonrpc": "2.0", "id": jsonrpc_id, "error": {"code": -32601, "message": "Method not found"}}


async def run_cli_execution(tool: ToolRegistry, metadata: ToolExecutionMetadata, action: str, args: Dict[str, Any], principal: Dict[str, Any]):
    """
    Execute a CLI command in a secure subprocess with structured semantic tracing.
    """
    logger.info(
        "CLI execution path entered",
        routing_choice="CLI",
        backend_used="subprocess",
        tool_name=tool.name,
        action=action,
        reconciliation_steps="authz_enforcement,cli_arg_construction",
        ontological_interpretation=f"CLI chosen for token efficiency; tool '{tool.name}' action '{action}'",
    )
    try:
        token = principal.get("_raw_token")
        if not token:
            logger.warning("CLI execution aborted: missing EAT", tool_name=tool.name)
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Missing EAT token."}}
        payload = verify_engram_token(token)
        authz = SemanticAuthorizationService()
        args = authz.enforce(payload, tool, action, args)
    except HTTPException as exc:
        logger.error("CLI execution authz failure", tool_name=tool.name, error=exc.detail)
        return {"jsonrpc": "2.0", "error": {"code": -32001, "message": exc.detail}}

    # CLI Command construction
    params = _exec_params(metadata)
    cmd_base = params.get("cli_command", tool.name)
    env = {"ENGRAM_EAT": principal.get("_raw_token")}

    try:
        full_args = [f"--{k}={v}" for k, v in args.items()]
        logger.info(
            "CLI subprocess launched",
            command=cmd_base,
            arg_count=len(full_args),
            backend_used="subprocess",
        )
        result = subprocess.run([cmd_base] + full_args, capture_output=True, text=True, env=env)
        logger.info(
            "CLI subprocess completed",
            exit_code=result.returncode,
            stdout_len=len(result.stdout),
            stderr_len=len(result.stderr),
        )
        return {
            "jsonrpc": "2.0",
            "result": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        }
    except Exception as e:
        logger.error("CLI subprocess failed", error=str(e), command=cmd_base)
        return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}}

async def run_http_execution(tool: ToolRegistry, metadata: ToolExecutionMetadata, action: str, args: Dict[str, Any], principal: Dict[str, Any]):
    """
    Execute an HTTP/MCP tool call with structured semantic tracing.
    """
    logger.info(
        "HTTP/MCP execution path entered",
        routing_choice="HTTP/MCP",
        backend_used="http_client",
        tool_name=tool.name,
        action=action,
        reconciliation_steps="authz_enforcement,schema_adaptation",
        ontological_interpretation=f"MCP/HTTP chosen for schema richness; tool '{tool.name}' action '{action}'",
    )
    try:
        token = principal.get("_raw_token")
        if not token:
            logger.warning("HTTP execution aborted: missing EAT", tool_name=tool.name)
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Missing EAT token."}}
        payload = verify_engram_token(token)
        authz = SemanticAuthorizationService()
        _ = authz.enforce(payload, tool, action, args)
    except HTTPException as exc:
        logger.error("HTTP execution authz failure", tool_name=tool.name, error=exc.detail)
        return {"jsonrpc": "2.0", "error": {"code": -32001, "message": exc.detail}}
    logger.info(
        "HTTP/MCP execution completed",
        tool_name=tool.name,
        backend_used="http_client",
    )
    return {"jsonrpc": "2.0", "result": {"message": "HTTP tool call routed (mock result)"}}


def _exec_params(metadata: ToolExecutionMetadata) -> Dict[str, Any]:
    if getattr(metadata, "exec_params", None):
        return metadata.exec_params or {}
    if getattr(metadata, "metadata", None):
        return metadata.metadata or {}
    return {}


def _infer_task_description(
    tool: ToolRegistry,
    action_name: Optional[str],
    arguments: Dict[str, Any],
    provided: Optional[str],
) -> str:
    if provided:
        return provided
    parts = [tool.name, tool.description]
    if action_name:
        parts.append(f"Action: {action_name}")
    if arguments:
        parts.append(f"Args: {json.dumps(arguments)}")
    return " | ".join([p for p in parts if p])


def _estimate_result_tokens(result: Dict[str, Any]) -> int:
    try:
        payload = json.dumps(result)
    except Exception:
        payload = str(result)
    return estimate_tokens(payload)

@router.post("/tools/{tool_name}/validate")
async def validate_tool_schema(
    tool_name: str,
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Validates a tool's current schema against the real backend state
    using OWL ontology and ML embeddings to detect drift.
    """
    from app.reconciliation.engine import reconciliation_engine
    
    current_schema = body.get("current_schema") or {}
    
    # In a production scenario, we might also trigger a re-discovery 
    # of the tool's source (API/CLI) here.
    
    corrected = await reconciliation_engine.validate_tool_drift(tool_name, current_schema)
    
    if corrected:
        return {
            "drift": True,
            "tool": tool_name,
            "corrected_schema": corrected,
            "message": "Semantic drift detected and corrected schema generated."
        }
    
    return {"drift": False, "tool": tool_name}


# --- Helper to register the router ---
# Usually done in main.py
