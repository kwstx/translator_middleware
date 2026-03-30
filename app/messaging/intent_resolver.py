import structlog
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
import re
from sqlmodel import select
from app.db.models import AgentRegistry

logger = structlog.get_logger(__name__)

class AtomicTask(BaseModel):
    """
    Represents a single, normalized task extracted from a complex user prompt.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: str = Field(..., description="The detected intent (e.g., 'translate', 'discover', 'delegate', 'check_status')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters stripped of ambient language.")
    confidence: float = Field(default=1.0)
    capability_tag: Optional[str] = Field(None, description="The specific agent capability tag this task maps to.")

class IntentResolutionResult(BaseModel):
    """
    The result of decomposing a complex prompt into atomic tasks.
    """
    original_prompt: str
    tasks: List[AtomicTask]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IntentResolver:
    """
    Sophisticated Natural Language Intent Resolution Layer.
    Decomposes complex, non-standard user prompts into normalized atomic tasks.
    """
    
    def __init__(self, capability_registry: Optional[Any] = None):
        self.capability_registry = capability_registry
        # In a real implementation, this would load a pre-trained transformer model (e.g., BERT/T5/LLM)
        self._model_ready = True
        logger.info("IntentResolver initialized with transformer-ready architecture.")

    async def resolve(self, prompt: str, db: Optional[Any] = None) -> IntentResolutionResult:
        """
        Parses arbitrary user input, maps it to specific agent capability tags,
        and strips ambient language.
        """
        logger.info("Resolving intent from prompt", prompt=prompt)
        
        segments = self._decompose_prompt(prompt)
        
        atomic_tasks = []
        for segment in segments:
            task = self._parse_segment(segment)
            if task:
                if db:
                    task.capability_tag = await self._map_to_registry_capability(task, db)
                else:
                    task.capability_tag = self._map_to_capability_sync(task)
                atomic_tasks.append(task)
        
        return IntentResolutionResult(
            original_prompt=prompt,
            tasks=atomic_tasks,
            metadata={"segments_processed": len(segments)}
        )

    async def _map_to_registry_capability(self, task: AtomicTask, db: Any) -> Optional[str]:
        """
        Queries the AgentRegistry to find the most relevant capability tag.
        """
        # 1. Search for direct keyword match in capabilities/semantic_tags
        query = select(AgentRegistry)
        result = await db.execute(query)
        agents = result.scalars().all()
        
        best_match = None
        for agent in agents:
            # Check if any capability matches the intent
            for cap in (agent.capabilities or []):
                if task.intent in cap.lower():
                    return cap
            for tag in (agent.semantic_tags or []):
                if task.intent in tag.lower():
                    return tag
                    
        return self._map_to_capability_sync(task)

    def resolve_sync(self, prompt: str) -> IntentResolutionResult:
        """
        Synchronous version of resolve() for use in legacy non-async contexts.
        """
        logger.debug("Resolving intent (sync)", prompt=prompt)
        segments = self._decompose_prompt(prompt)
        atomic_tasks = []
        for segment in segments:
            task = self._parse_segment(segment)
            if task:
                # Synchronous capability mapping
                task.capability_tag = self._map_to_capability_sync(task)
                atomic_tasks.append(task)
        
        return IntentResolutionResult(
            original_prompt=prompt,
            tasks=atomic_tasks,
            metadata={"segments_processed": len(segments)}
        )

    def _map_to_capability_sync(self, task: AtomicTask) -> str:
        mapping = {
            "translate": "universal_translation",
            "predict": "market_forecasting",
            "check_status": "task_monitoring",
            "discover": "agent_discovery"
        }
        return mapping.get(task.intent, "general_purpose")

    def _decompose_prompt(self, prompt: str) -> List[str]:
        """
        Splits a complex prompt into independent task segments.
        Handles connectors like 'and', 'then', 'also', plus punctuation.
        """
        # Split by common conjunctions and sentence delimiters
        delimiters = r"\.|\band\b|\bthen\b|\balso\b|\;|\,"
        segments = re.split(delimiters, prompt, flags=re.IGNORECASE)
        # Clean up whitespace and empty segments
        return [s.strip() for s in segments if s.strip()]

    def _parse_segment(self, segment: str) -> Optional[AtomicTask]:
        """
        Extracts intent and parameters from a single segment.
        Strips ambient language like "please", "can you", "I want to".
        """
        clean_segment = segment.lower()
        ambient_patterns = [
            r"^please\s+", r"^can\s+you\s+", r"^i\s+want\s+to\s+", 
            r"^could\s+you\s+", r"^help\s+me\s+", r"^go\s+ahead\s+and\s+"
        ]
        for pattern in ambient_patterns:
            clean_segment = re.sub(pattern, "", clean_segment).strip()

        # Simple but effective intent classification rules (mocking the transformer top layer)
        if any(w in clean_segment for w in ["translate", "convert", "transform"]):
            return AtomicTask(
                intent="translate",
                parameters=self._extract_parameters(clean_segment, "translate"),
                confidence=0.95
            )
        elif any(w in clean_segment for w in ["predict", "market", "price", "forecast"]):
            return AtomicTask(
                intent="predict",
                parameters=self._extract_parameters(clean_segment, "predict"),
                confidence=0.92
            )
        elif any(w in clean_segment for w in ["status", "where is", "progress"]):
            return AtomicTask(
                intent="check_status",
                parameters=self._extract_parameters(clean_segment, "check_status"),
                confidence=0.88
            )
        elif any(w in clean_segment for w in ["find", "discover", "search", "who can"]):
            return AtomicTask(
                intent="discover",
                parameters=self._extract_parameters(clean_segment, "discover"),
                confidence=0.90
            )
        
        # Default fallback
        return AtomicTask(
            intent="general_query",
            parameters={"content": segment},
            confidence=0.5
        )

    def _extract_parameters(self, segment: str, intent: str) -> Dict[str, Any]:
        """
        Extracts core request parameters while stripping ambient language.
        """
        params = {}
        if intent == "translate":
            # Extract target protocol if mentioned
            match = re.search(r"to\s+([a-zA-Z0-9]+)", segment)
            if match:
                params["target_protocol"] = match.group(1).upper()
            
            # Extract content (strip "translate" and "to XXX")
            content = re.sub(r"translate|convert|transform", "", segment).strip()
            content = re.sub(r"to\s+[a-zA-Z0-9]+", "", content).strip()
            params["content"] = content
            
        elif intent == "predict":
            # Extract market/symbol
            # Simple heuristic: last words
            params["market"] = segment.split()[-1]
            params["content"] = segment
            
        elif intent == "check_status":
            # Look for IDs
            id_match = re.search(r"([a-fA-F0-9\-]{32,})", segment)
            if id_match:
                params["task_id"] = id_match.group(1)
            params["content"] = segment
            
        return params

    async def _map_to_capability(self, task: AtomicTask) -> str:
        """
        Maps a task to a specific capability tag in the registry.
        """
        # Logic to match task.intent + params to AgentRegistry.capabilities or ToolRegistry.tags
        mapping = {
            "translate": "universal_translation",
            "predict": "market_forecasting",
            "check_status": "task_monitoring",
            "discover": "agent_discovery"
        }
        return mapping.get(task.intent, "general_purpose")

# Shared instance if needed
intent_resolver = IntentResolver()
