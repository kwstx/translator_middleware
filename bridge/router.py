from typing import Any, Dict, Optional
from app.messaging.orchestrator import Orchestrator
import structlog

logger = structlog.get_logger(__name__)

# Singleton orchestrator for the bridge
_orchestrator = Orchestrator()

from reliability.middleware import wrap_route_to

@wrap_route_to
async def routeTo(
    target: str,
    payload: Any,
    correlation_id: str = "default",
    retry_count: int = 0,
    **options: Any
) -> Dict[str, Any]:
    """
    Unified entrypoint for routing inter-agent messages.
    This is the target for the Reliability Middleware.
    """
    # This will be wrapped/called by reliability middleware
    source_protocol = options.get("source_protocol", "A2A")
    eat = options.get("eat")
    
    result = await _orchestrator.handoff_async(
        source_message=payload,
        source_protocol=source_protocol,
        target_protocol=target,
        eat=eat
    )
    
    return result.translated_message
