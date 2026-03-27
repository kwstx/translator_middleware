import abc
import structlog
import asyncio
from typing import Any, Dict, Optional, List
from app.core.metrics import record_translation_error, record_translation_success
from app.core.translator import TranslatorEngine
from app.semantic.mapper import SemanticMapper
from app.core.config import settings

logger = structlog.get_logger(__name__)

class BaseConnector(abc.ABC):
    """
    Abstract base class for all tool connectors.
    Each connector translates between Engram's unified MCP format
    and the tool's proprietary API format.
    """

    def __init__(self, name: str, source_protocol: str = "MCP"):
        self.name = name
        self.source_protocol = source_protocol
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
        If 'db' and 'user_id' are provided, the connector can retrieve the user's specific credentials.
        """
        pass

    def reconcile_schema(self, data: Dict[str, Any], target_protocol: str) -> Dict[str, Any]:
        """
        Reconciles data schema using the SemanticMapper's DataSiloResolver.
        """
        # Placeholder schemas for demonstration; in production, these would be loaded from a registry
        source_schema = {"type": "object", "properties": {}}
        target_schema = {"type": "object", "properties": {}}
        
        try:
            return self._mapper.DataSiloResolver(
                source_data=data,
                source_schema=source_schema,
                target_schema=target_schema,
                source_protocol=self.source_protocol,
                target_protocol=target_protocol
            )
        except Exception as e:
            logger.warning("Connector: schema reconciliation failed", connector=self.name, error=str(e))
            return data

    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Maps tool-specific error codes and exceptions to Engram's unified error format.
        """
        error_type = type(error).__name__
        detail = str(error)
        
        # Mapping common tool errors (extendable per connector)
        status_code = getattr(error, "status_code", 500)
        
        return {
            "status": "error",
            "connector": self.name,
            "error_type": error_type,
            "detail": detail,
            "engram_code": "TOOL_EXECUTION_FAILURE" if status_code >= 500 else "BAD_TOOL_REQUEST"
        }

    async def execute(self, message: Dict[str, Any], message_protocol: str, db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        The main entry point for executing a task via the connector.
        Supports single tasks and multi-step sequential workflows.
        """
        # 1. Normalization
        normalized_task = message
        if message_protocol.upper() != "MCP":
            try:
                normalized_task = self._translator.translate(message, message_protocol, "MCP")
                logger.info("Connector: payload normalized", connector=self.name, source_p=message_protocol, to="MCP")
            except Exception as e:
                logger.warning("Connector: normalization failed, using raw message", connector=self.name, error=str(e))
                normalized_task = message

        try:
            # 2. Check for multi-step workflow in the task
            workflow_steps = normalized_task.get("workflow", [])
            if workflow_steps and isinstance(workflow_steps, list):
                return await self._execute_workflow(workflow_steps, normalized_task, db, user_id)

            # 3. Standard single-step execution
            # Reconcile schema before translating to tool
            reconciled_task = self.reconcile_schema(normalized_task, self.name.upper())
            
            tool_request = self.translate_to_tool(reconciled_task)
            logger.debug("Connector: translated to tool format", connector=self.name, request=tool_request)

            tool_response = await self.call_tool(tool_request, db, user_id)
            logger.debug("Connector: received tool response", connector=self.name)

            final_response = self.translate_from_tool(tool_response)
            
            record_translation_success(f"connector_{self.name.lower()}", message_protocol, self.name.upper())
            return final_response

        except Exception as e:
            logger.error("Connector: execution failed", connector=self.name, error=str(e))
            record_translation_error(f"connector_{self.name.lower()}", message_protocol, self.name.upper())
            return self.handle_error(e)

    async def _execute_workflow(self, steps: List[Dict[str, Any]], context: Dict[str, Any], db: Optional[Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a sequence of steps, passing the output of one as context to the next.
        """
        logger.info("Connector: starting multi-step workflow", connector=self.name, step_count=len(steps))
        current_context = context.copy()
        history = []

        for i, step in enumerate(steps):
            logger.info("Connector: executing workflow step", connector=self.name, step=i+1, total=len(steps))
            
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
                else:
                    logger.error("Connector: workflow step failed", connector=self.name, step=i+1)
                    return {
                        "status": "error",
                        "connector": self.name,
                        "error": f"Workflow failed at step {i+1}",
                        "history": history,
                        "failed_step": step_final
                    }
            except Exception as e:
                return self.handle_error(e)

        return {
            "status": "success",
            "connector": self.name,
            "message": "Workflow completed successfully",
            "history": history,
            "final_payload": current_context
        }
