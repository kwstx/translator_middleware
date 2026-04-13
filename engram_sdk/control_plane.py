from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Tuple, TYPE_CHECKING
import structlog

if TYPE_CHECKING:
    from .client import EngramSDK

from .scope import Scope
from .global_data import get_global_data, GlobalData

logger = structlog.get_logger(__name__)

from .types import ToolCall

class Step:
    """
    Defines a narrow list of allowed tools or functions for a specific moment 
    in the workflow, along with preconditions that must be satisfied and 
    transitions to the next step.
    """
    def __init__(
        self,
        name: str,
        tools: List[str],
        next_step: Optional[str] = None,
        preconditions: Optional[List[str]] = None,
        handler: Optional[Callable[[Any, GlobalData], Tuple[Optional[str], Any]]] = None,
        required_fields: Optional[List[str]] = None,
        description: Optional[str] = None,
        role_guidance: Optional[str] = None
    ):
        self.name = name
        self.tools = tools
        self.next_step = next_step
        self.preconditions = preconditions or []
        self.handler = handler
        self.required_fields = required_fields or []
        self.description = description
        self.role_guidance = role_guidance

    def validate_preconditions(self, data_store: GlobalData) -> bool:
        """Verifies that all required context from prior steps is satisfied."""
        missing = [p for p in self.preconditions if data_store.get(p) is None]
        if missing:
            logger.error("step_precondition_failed", step=self.name, missing=missing)
            return False
        return True

STANDARD_ROLE_GUIDANCE = (
    "You are a specialized agent participating in a governed tool-use workflow. "
    "Execute the provided tools to satisfy the current turn's objective. "
    "Decision-making regarding the overall sequence, data flow, and workflow "
    "transitions is handled by the ControlPlane. Do not attempt to plan or "
    "sequence subsequent steps."
)

class ControlPlane:
    """
    Acts as the central state machine and enforces Programmatic Governed Inference (PGI).
    
    The ControlPlane owns the workflow sequence for data collection. It ensures 
    the model never decides the order of steps or data gathering, enforcing 
    strict sequencing so each piece of info is collected at the exact right moment.
    """
    
    def __init__(self, sdk: EngramSDK):
        self.sdk = sdk
        self.steps: Dict[str, Step] = {}
        self.global_data = get_global_data()
        self.current_step_name: Optional[str] = None
        self.tool_handlers: Dict[str, Callable] = {}
        self.role_guidance: str = STANDARD_ROLE_GUIDANCE

    def register_tool_handler(self, tool_name: str, handler: Callable) -> ControlPlane:
        """Maps a tool name to its local implementation function."""
        self.tool_handlers[tool_name] = handler
        return self

    def reset_global_data(self) -> None:
        """Clears all data from the global store."""
        self.global_data.clear()

    def add_step(
        self, 
        name: str, 
        tools: List[str], 
        handler: Optional[Callable[[Any, GlobalData], Tuple[Optional[str], Any]]] = None,
        required_fields: Optional[List[str]] = None,
        next_step: Optional[str] = None,
        preconditions: Optional[List[str]] = None,
        description: Optional[str] = None,
        role_guidance: Optional[str] = None
    ) -> ControlPlane:
        """
        Adds a governed data collection step to the state machine.
        
        Args:
            name: Unique ID for this step.
            tools: List of tool names allowed during this step.
            handler: Optional thick function for custom logic. 
                    Signature: (model_output, context) -> (next_step, data).
            required_fields: Optional list of keys that MUST be present in 
                            the model's JSON output for this step to succeed.
            next_step: Default transition if no handler is provided or if it returns it.
            preconditions: List of context keys that must exist before this step starts.
            description: Metadata about the data being gathered.
            role_guidance: Optional custom thin instruction for this specific step.
        """
        self.steps[name] = Step(
            name=name,
            tools=tools,
            handler=handler,
            required_fields=required_fields,
            next_step=next_step,
            preconditions=preconditions,
            description=description,
            role_guidance=role_guidance
        )
        return self

    def get_system_prompt(self, step_name: str) -> str:
        """
        Generates an extremely thin system prompt for the current step.
        Contains only basic role guidance and the current step's description.
        All sequencing logic remains strictly in the ControlPlane.
        """
        step = self.steps.get(step_name)
        guidance = (step.role_guidance if step and step.role_guidance 
                    else self.role_guidance)
        
        prompt = f"{guidance}\n\n"
        if step and step.description:
            prompt += f"CURRENT OBJECTIVE: {step.description}\n"
        
        return prompt.strip()

    def run(
        self, 
        initial_step: str, 
        initial_data: Any, 
        inference_fn: Callable[[str, Scope, Any, str], Any]
    ) -> Any:
        """
        Executes the governed sequence starting from the initial step.
        """
        self.current_step_name = initial_step
        current_data = initial_data
        
        logger.info("starting_governed_sequence", initial_step=initial_step)
        
        while self.current_step_name:
            step = self.steps.get(self.current_step_name)
            if not step:
                raise ValueError(f"Step '{self.current_step_name}' not defined.")
            
            # 1. Enforce Preconditions
            if not step.validate_preconditions(self.global_data):
                missing = [p for p in step.preconditions if self.global_data.get(p) is None]
                raise ValueError(f"Step '{self.current_step_name}' failed preconditions. Missing: {missing}")

            # 2. Enforce Tool Governance (Narrow Scope)
            step_scope = Scope(
                tools=step.tools, 
                step_id=f"pgi_{self.current_step_name}_{self.sdk.agent_id or 'anon'}"
            )
            step_scope._sdk = self.sdk
            
            logger.info("collecting_data", step=self.current_step_name, tools=step.tools)
            
            with step_scope:
                # 3. Governed Inference (Thin Prompt)
                system_prompt = self.get_system_prompt(self.current_step_name)
                model_output = inference_fn(
                    self.current_step_name, 
                    step_scope, 
                    current_data, 
                    system_prompt
                )
                
                # 4. Strict Sequence Validation
                if step.required_fields:
                    if not isinstance(model_output, dict):
                        raise ValueError(f"Step '{self.current_step_name}' expected dict output, got {type(model_output)}")
                    
                    missing = [f for f in step.required_fields if f not in model_output]
                    if missing:
                        logger.warning("missing_required_data", step=self.current_step_name, missing=missing)
                        raise ValueError(f"Strict sequencing violation: Step '{self.current_step_name}' failed to collect {missing}")

                # 5. Programmatic Transition
                # Handler takes precedence, then default next_step.
                if step.handler:
                    next_step, next_data = step.handler(model_output, self.global_data)
                else:
                    next_step = step.next_step
                    next_data = model_output
                
                logger.info(
                    "transitioning", 
                    from_step=self.current_step_name, 
                    to_step=next_step
                )
                
                self.current_step_name = next_step
                current_data = next_data

        return current_data

    def drive(
        self, 
        initial_step: str, 
        inference_fn: Callable[[str, Scope, str], ToolCall]
    ) -> Any:
        """
        Strict Orchestrator: Drives the governed workflow turn-by-turn.
        
        For each step:
        1. Activates the current Step and enforces preconditions.
        2. Supplies ONLY validated tools for that Step to the model via Scope.
        3. Executes the chosen tool and writes results to GlobalData.
        4. Automatically advances to the next Step.
        """
        self.current_step_name = initial_step
        
        logger.info("orchestrator_started", initial_step=initial_step)
        
        while self.current_step_name:
            step = self.steps.get(self.current_step_name)
            if not step:
                raise ValueError(f"Step '{self.current_step_name}' not defined.")
            
            # 1. Enforce Preconditions
            if not step.validate_preconditions(self.global_data):
                missing = [p for p in step.preconditions if self.global_data.get(p) is None]
                raise ValueError(f"Step '{self.current_step_name}' failed preconditions. Missing: {missing}")

            # 2. Narrow Scope + Governed Turn
            with self.sdk.scope(step.name, tools=step.tools) as scope:
                logger.info("orchestrator_step_active", step=step.name, allowed_tools=step.tools)
                
                # Call model with Thin Prompt role guidance
                system_prompt = self.get_system_prompt(self.current_step_name)
                tool_call = inference_fn(self.current_step_name, scope, system_prompt)
                
                # Governance Check: Did the model call a permitted tool?
                if tool_call.name not in step.tools:
                    logger.error("governance_violation", step=step.name, attempted_tool=tool_call.name)
                    raise ValueError(f"Step '{step.name}' violation: Tool '{tool_call.name}' is not allowed.")

                # 3. Execute Tool
                handler = self.tool_handlers.get(tool_call.name)
                if not handler:
                    logger.error("tool_handler_missing", tool=tool_call.name)
                    raise ValueError(f"No handler registered for tool '{tool_call.name}'")

                logger.info("executing_governed_tool", tool=tool_call.name)
                result = handler(**tool_call.arguments)
                
                # 4. Write Results to GlobalData
                # Store the raw return value in a step-specific key
                result_key = f"{step.name}_output"
                self.global_data.set(result_key, result)
                
                # 5. Programmatic Transition
                if step.handler:
                    # Custom handler can decide next step based on tool output
                    next_step, _ = step.handler(result, self.global_data)
                else:
                    # Default to predefined next_step
                    next_step = step.next_step
                
                logger.info("orchestrator_transition", from_step=step.name, to_step=next_step)
                self.current_step_name = next_step
                
        logger.info("orchestrator_finished")
        return self.global_data.all()
