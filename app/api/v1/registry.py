import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session, select
import structlog
from app.db.session import get_session
from app.core.security import get_current_principal, verify_engram_token
from app.core.semantic_auth import SemanticAuthorizationService
import subprocess
from app.db.models import ToolRegistry, ToolExecutionMetadata, ExecutionType, AgentRegistry
from app.services.registry_service import RegistryService

router = APIRouter(prefix="/registry", tags=["Registry"])
logger = structlog.get_logger(__name__)

# --- Ingestion Endpoints ---

@router.post("/ingest/openapi", status_code=status.HTTP_201_CREATED)
async def ingest_openapi(
    url_or_path: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    db: Session = Depends(get_session)
):
    """
    Ingests an OpenAPI spec and registers its tools.
    """
    service = RegistryService(db)
    agent_uuid = uuid.UUID(agent_id)
    tool = await service.ingest_openapi(url_or_path, agent_uuid)
    return tool

@router.post("/ingest/cli", status_code=status.HTTP_201_CREATED)
async def ingest_cli(
    command: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    db: Session = Depends(get_session)
):
    """
    Ingests a CLI tool by parsing its --help output.
    """
    service = RegistryService(db)
    agent_uuid = uuid.UUID(agent_id)
    tool = await service.ingest_cli_help(command, agent_uuid)
    return tool

@router.get("/tools")
async def list_tools(db: Session = Depends(get_session)):
    """
    List all registered tools.
    """
    tools = db.exec(select(ToolRegistry)).all()
    return tools

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
        tools = db.exec(select(ToolRegistry)).all()
        result = [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "actions": t.actions or [],
                "input_schema": t.input_schema or {}
            }
            for t in tools
        ]
        return {"jsonrpc": "2.0", "id": jsonrpc_id, "result": {"tools": result}}

    if method == "mcp.call_tool":
        tool_id = params.get("tool_id")
        action_name = params.get("action")
        arguments = params.get("arguments", {})

        tool = db.get(ToolRegistry, uuid.UUID(tool_id))
        if not tool:
            return {"jsonrpc": "2.0", "id": jsonrpc_id, "error": {"code": -32601, "message": "Tool not found"}}

        # Determine execution path
        metadata = tool.execution_metadata
        if metadata.execution_type == ExecutionType.CLI:
            # Route to CLI executor
            return await run_cli_execution(tool, metadata, action_name, arguments, principal)
        
        elif metadata.execution_type == ExecutionType.HTTP:
            # Route to HTTP/REST executor
            return await run_http_execution(tool, metadata, action_name, arguments, principal)

        return {"jsonrpc": "2.0", "id": jsonrpc_id, "error": {"code": -32603, "message": "Execution type not supported yet"}}

    return {"jsonrpc": "2.0", "id": jsonrpc_id, "error": {"code": -32601, "message": "Method not found"}}


async def run_cli_execution(tool: ToolRegistry, metadata: ToolExecutionMetadata, action: str, args: Dict[str, Any], principal: Dict[str, Any]):
    """
    Execute a CLI command in a secure subprocess.
    """
    try:
        token = principal.get("_raw_token")
        if not token:
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Missing EAT token."}}
        payload = verify_engram_token(token)
        authz = SemanticAuthorizationService()
        args = authz.enforce(payload, tool, action, args)
    except HTTPException as exc:
        return {"jsonrpc": "2.0", "error": {"code": -32001, "message": exc.detail}}

    # CLI Command construction
    cmd_base = metadata.metadata.get("cli_command", tool.name)
    # Inject auth env vars from principal/EAT
    env = {"ENGRAM_EAT": principal.get("_raw_token")}
    
    # Secure subprocess call (Using docker if available, fallback to direct in sandbox)
    try:
        # Mock/Simplified isolated run
        # In production, this would use a Docker SDK to spin up a container
        full_args = [f"--{k}={v}" for k,v in args.items()]
        result = subprocess.run([cmd_base] + full_args, capture_output=True, text=True, env=env)
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        }
    except Exception as e:
        return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}}

async def run_http_execution(tool: ToolRegistry, metadata: ToolExecutionMetadata, action: str, args: Dict[str, Any], principal: Dict[str, Any]):
    try:
        token = principal.get("_raw_token")
        if not token:
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Missing EAT token."}}
        payload = verify_engram_token(token)
        authz = SemanticAuthorizationService()
        _ = authz.enforce(payload, tool, action, args)
    except HTTPException as exc:
        return {"jsonrpc": "2.0", "error": {"code": -32001, "message": exc.detail}}
    # HTTP orchestration
    return {"jsonrpc": "2.0", "result": {"message": "HTTP tool call routed (mock result)"}}

# --- Helper to register the router ---
# Usually done in main.py
