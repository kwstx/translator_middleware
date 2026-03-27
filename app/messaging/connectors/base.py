import abc
import structlog
import asyncio
import time
from typing import Any, Dict, Optional, List
from app.core.metrics import record_translation_error, record_translation_success, record_connector_call
from app.core.translator import TranslatorEngine
from app.semantic.mapper import SemanticMapper
from app.core.config import settings
from app.core.logging import bind_context

logger = structlog.get_logger(__name__)

class BaseConnector(abc.ABC):
    """
    Abstract base class for all tool connectors.
    Each connector translates between Engram's unified MCP format
    and the tool's proprietary API format.
    """

    def __init__(
        self, 
        name: str, 
        source_protocol: str = "MCP", 
        mapping_rules: Optional[Dict[str, str]] = None,
        source_schema: Optional[Dict[str, Any]] = None,
        target_schema: Optional[Dict[str, Any]] = None
    ):
        self.name = name.upper()
        self.source_protocol = source_protocol
        self.mapping_rules = mapping_rules or {}
        self.source_schema = source_schema or {"type": "object", "properties": {}}
        self.target_schema = target_schema or {"type": "object", "properties": {}}
        self._translator = TranslatorEngine()
        self._mapper = SemanticMapper(settings.ONTOLOGY_PATH if hasattr(settings, "ONTOLOGY_PATH") else "app/semantic/protocols.owl")

    @abc.abstractmethod
    def translate_to_tool(self, engram_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts Engram's unified task format (MCP) to the tool's API request format.
        """
        pass

    @abc.abstractmethod
    def translate_from_tool(self, tool_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts the tool's response back into Engram's unified output format.
        """
        pass

    @abc.abstractmethod
    async def call_tool(self, tool_request: Dict[str, Any], db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs the actual API call to the tool.
        """
        pass

    async def get_active_token(self, db: Optional[Any], user_id: Optional[str], default_token: Optional[str] = None) -> Optional[str]:
        """
        Helper to retrieve the user's specific credential with automatic refresh support.
        """
        from uuid import UUID
        from app.services.credentials import CredentialService
        
        if db and user_id:
            try:
                token = await CredentialService.get_active_token(db, UUID(user_id), self.name.lower())
                if token:
                    logger.info("Connector using user-specific token")
                    return token
            except Exception as e:
                logger.warning("Connector: failed to retrieve user credentials", error=str(e))
        
        return default_token

    def reconcile_schema(self, data: Dict[str, Any], target_protocol: str) -> Dict[str, Any]:
        """
        Reconciles data schema using the SemanticMapper's DataSiloResolver.
        Uses connector-specific mapping rules if provided.
        """
        try:
            return self._mapper.DataSiloResolver(
                source_data=data,
                source_schema=self.source_schema,
                target_schema=self.target_schema,
                source_protocol=self.source_protocol,
                target_protocol=target_protocol,
                custom_rules=self.mapping_rules
            )
        except Exception as e:
            logger.warning("Schema reconciliation failed", error=str(e))
            return data

    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Maps tool-specific error codes and exceptions to Engram's unified error format.
        """
        error_type = type(error).__name__
        detail = str(error).lower()
        
        status_code = getattr(error, "status_code", 500)
        if hasattr(error, "response") and hasattr(error.response, "status_code"):
            status_code = error.response.status_code
        
        is_timeout = "timeout" in detail or "timed out" in detail
        
        engram_code = "TOOL_EXECUTION_FAILURE"
        is_transient = False
        action_required = None

        if status_code == 429 or "rate limit" in detail or "too many requests" in detail:
            engram_code = "TRANSIENT_TOOL_ERROR"
            error_type = "RateLimitError"
            is_transient = True
        elif status_code in (502, 503, 504) or is_timeout or "connection" in detail:
            engram_code = "TRANSIENT_TOOL_ERROR"
            error_type = "NetworkError"
            is_transient = True
        elif status_code == 401 or "unauthorized" in detail or "invalid api key" in detail:
            engram_code = "AUTH_FAILURE"
            error_type = "InvalidCredentialsError"
        elif "expired" in detail or ("token" in detail and "refresh" in detail):
            engram_code = "AUTH_FAILURE"
            error_type = "ExpiredTokenError"
            action_required = "REFRESH_CREDENTIALS"
        elif status_code >= 400 and status_code < 500:
            engram_code = "BAD_TOOL_REQUEST"

        return {
            "status": "error",
            "connector": self.name,
            "error_type": error_type,
            "detail": str(error),
            "engram_code": engram_code,
            "is_transient": is_transient,
            "action_required": action_required
        }

    async def execute(self, message: Dict[str, Any], message_protocol: str, db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        The main entry point for executing a task via the connector.
        """
        bind_context(connector=self.name, user_id=user_id)
        start_time = time.time()
        
        # 1. Normalization
        normalized_task = message
        if message_protocol.upper() != "MCP":
            try:
                normalized_task = self._translator.translate(message, message_protocol, "MCP")
                logger.info("Connector payload normalized", source_protocol=message_protocol)
            except Exception as e:
                logger.warning("Normalization failed, using raw message", error=str(e))
                normalized_task = message

        try:
            # 2. Check for multi-step workflow in the task
            workflow_steps = normalized_task.get("workflow", [])
            if workflow_steps and isinstance(workflow_steps, list):
                return await self._execute_workflow(workflow_steps, normalized_task, db, user_id)

            # 3. Standard single-step execution
            reconciled_task = self.reconcile_schema(normalized_task, self.name.upper())
            tool_request = self.translate_to_tool(reconciled_task)
            logger.debug("Connector: translated request", request=tool_request)

            tool_response = await self.call_tool(tool_request, db, user_id)
            logger.debug("Connector: received response")

            final_response = self.translate_from_tool(tool_response)
            
            duration = time.time() - start_time
            record_translation_success(f"connector_{self.name.lower()}", message_protocol, self.name.upper())
            record_connector_call(self.name, user_id or "unknown", "success", duration)
            
            logger.info("Connector execution successful", duration=duration)
            return final_response

        except Exception as e:
            duration = time.time() - start_time
            logger.error("Connector execution failed", error=str(e), duration=duration)
            record_translation_error(f"connector_{self.name.lower()}", message_protocol, self.name.upper())
            record_connector_call(self.name, user_id or "unknown", "error", duration)
            return self.handle_error(e)

    async def _execute_workflow(self, steps: List[Dict[str, Any]], context: Dict[str, Any], db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a sequence of steps, passing the output of one as context to the next.
        """
        logger.info("Starting multi-step workflow", step_count=len(steps))
        current_context = context.copy()
        history = []

        for i, step in enumerate(steps):
            logger.info("Executing workflow step", step=i+1, total=len(steps))
            step_start_time = time.time()
            
            # Merge context into step
            step_task = {**current_context, **step}
            
            # Reconcile and translate
            reconciled_step = self.reconcile_schema(step_task, self.name.upper())
            tool_req = self.translate_to_tool(reconciled_step)
            
            # Call tool
            try:
                step_resp = await self.call_tool(tool_req, db, user_id)
                step_final = self.translate_from_tool(step_resp)
                
                # Update context with output for next step
                if step_final.get("status") == "success":
                    payload = step_final.get("payload", {})
                    current_context.update(payload)
                    history.append({"step": i+1, "status": "success", "result": step_final})
                    logger.info("Workflow step successful", step=i+1)
                else:
                    logger.error("Workflow step failed", step=i+1)
                    return {
                        "status": "error",
                        "connector": self.name,
                        "error": f"Workflow failed at step {i+1}",
                        "history": history,
                        "failed_step": step_final
                    }
            except Exception as e:
                logger.error("Workflow step exception", step=i+1, error=str(e))
                return self.handle_error(e)

        return {
            "status": "success",
            "connector": self.name,
            "message": "Workflow completed successfully",
            "history": history,
            "final_payload": current_context
        }
