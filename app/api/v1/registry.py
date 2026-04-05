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
        user_id = principal.get("sub")
        
        stmt = select(ToolRegistry)
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                stmt = stmt.where(ToolRegistry.user_id == user_uuid)
            except (ValueError, TypeError):
                # Fallback for old identity tokens
                pass
            
        results = await db.execute(stmt)
        raw_tools = results.scalars().all()
        
        # Pre-routing step to dynamically dynamically filter the tool list
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
            task_description = _infer_task_description(tool, action_name, arguments, task_description)
            backends = available_backends(tool, metadata)
            stats = await fetch_backend_stats(db, tool.id, backends)
            stats = {
                backend: estimate_backend_stats(tool, metadata, backend, task_description, stats.get(backend))
                for backend in backends
            }
            decision = route_tool_backend_sync(tool, metadata, task_description, stats)
            decision_record = await log_routing_decision(db, tool.id, action_name, decision)

            import structlog
            structlog.contextvars.bind_contextvars(
                routing_choice=decision.backend,
                backend_used=decision.backend,
                ontological_interpretations=f"Mapped '{action_name or 'default'}' to ontology '{tool.name}'",
                reconciliation_steps="schema_compression_and_validation"
            )
            logger.info(
                "Execution Path Triggered",
                tool_id=str(tool.id),
                routing_choice=decision.backend,
                backend_used=decision.backend,
                ontological_interpretations=f"Mapped '{action_name or 'default'}' to ontology '{tool.name}'",
                reconciliation_steps="schema_compression_and_validation",
                execution_type=decision.backend
            )

            start = time.perf_counter()
            error_message = None
            try:
                if decision.backend == CLI_BACKEND:
                    result = await run_cli_execution(tool, metadata, action_name, arguments, principal)
                elif decision.backend in {MCP_BACKEND, HTTP_BACKEND}:
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
                    routing_choice=decision.backend,
                    backend_used=decision.backend,
                    similarity_score=best.similarity if best else 0.0,
                    composite_score=best.composite_score if best else 0.0,
                    token_cost_est=best.token_cost_est if best else 0.0,
                    context_overhead_est=best.context_overhead_est if best else 0.0,
                    reconciliation_steps=["authz_enforcement", "schema_compression", "backend_routing"],
                    ontological_interpretation=(
                        f"{decision.backend} chosen for "
                        f"{'token efficiency' if decision.backend == CLI_BACKEND else 'schema richness'}; "
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

# --- Helper to register the router ---
# Usually done in main.py
