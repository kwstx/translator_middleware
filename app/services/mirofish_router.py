"""
MiroFish Swarm Router
=====================
Provides the server-side ``pipe_to_mirofish_swarm`` function that forwards
normalised inter-agent messages to a running MiroFish instance.

The function mirrors the TypeScript ``pipeToMiroFishSwarm`` in
``playground/src/mirofish-bridge.ts`` and is designed to be invoked by the
Orchestrator whenever the target platform equals ``mirofish``.

IMPORTANT — users must launch their own MiroFish instance with a valid
``LLM_API_KEY`` configured in its ``.env`` file before routing messages to
MiroFish.
"""

from typing import Any, Dict, Optional

import httpx
import structlog

from app.core.config import settings
from app.core.metrics import record_translation_error
from app.core.translator import TranslatorEngine

logger = structlog.get_logger(__name__)

# Module-level translator used to normalise payloads before injection.
_normalise_engine = TranslatorEngine()


async def pipe_to_mirofish_swarm(
    message: Any,
    external_data: Optional[Dict[str, Any]] = None,
    swarm_id: Optional[str] = None,
    num_agents: Optional[int] = None,
    mirofish_base_url: Optional[str] = None,
    source_protocol: Optional[str] = None,
) -> Dict[str, Any]:
    """Forward a normalised inter-agent message to a MiroFish swarm.

    Parameters
    ----------
    message:
        The raw inter-agent payload (any supported protocol envelope).
    external_data:
        Optional live context (prices, sentiment, headlines) to inject as
        God's-eye variables.  When ``None`` the swarm receives only the
        seed text derived from *message*.
    swarm_id:
        Target swarm identifier.  Falls back to
        ``settings.MIROFISH_DEFAULT_SWARM_ID``.
    num_agents:
        Number of agents to spin up.  Falls back to
        ``settings.MIROFISH_DEFAULT_NUM_AGENTS``.
    mirofish_base_url:
        Base URL of the user's MiroFish service.  Falls back to
        ``settings.MIROFISH_BASE_URL``.
    source_protocol:
        Protocol identifier of the incoming message (e.g. ``"A2A"``).
        When provided the payload is run through the existing translation
        layer (``TranslatorEngine``) to normalise it to MCP before
        injection, preserving semantic fidelity.

    Returns
    -------
    dict
        The response body from MiroFish (the compiled simulation report).
        If MiroFish is unreachable or returns a non-2xx status, a structured
        error payload is returned instead of raising.
    """

    resolved_base_url = (mirofish_base_url or settings.MIROFISH_BASE_URL).rstrip("/")
    resolved_swarm_id = swarm_id or settings.MIROFISH_DEFAULT_SWARM_ID
    resolved_num_agents = num_agents or settings.MIROFISH_DEFAULT_NUM_AGENTS

    # ------------------------------------------------------------------
    # 1. Normalise the payload using the existing translation layer so
    #    that semantic fidelity is preserved regardless of the originating
    #    protocol.
    # ------------------------------------------------------------------
    normalised_payload = message
    if source_protocol and source_protocol.upper() != "MCP" and isinstance(message, dict):
        try:
            normalised_payload = _normalise_engine.translate(
                message, source_protocol, "MCP"
            )
            logger.info(
                "MiroFish router: payload normalised",
                source_protocol=source_protocol,
                target_protocol="MCP",
            )
        except Exception as exc:
            logger.warning(
                "MiroFish router: normalisation failed, forwarding raw payload",
                source_protocol=source_protocol,
                error=str(exc),
            )
            normalised_payload = message

    # ------------------------------------------------------------------
    # 2. Build seedText from the normalised payload.
    # ------------------------------------------------------------------
    if isinstance(normalised_payload, dict):
        # Prefer an explicit seed_text field; otherwise serialise the whole
        # payload so MiroFish always receives usable context.
        import json

        seed_text = normalised_payload.get(
            "seed_text", json.dumps(normalised_payload, default=str)
        )
    else:
        seed_text = str(normalised_payload)

    # ------------------------------------------------------------------
    # 3. POST to the MiroFish simulation/start endpoint.
    # ------------------------------------------------------------------
    request_body: Dict[str, Any] = {
        "seedText": seed_text,
        "numAgents": resolved_num_agents,
        "swarmId": resolved_swarm_id,
    }
    if external_data:
        request_body["godsEyeVariables"] = external_data

    endpoint = f"{resolved_base_url}/api/simulation/start"

    logger.info(
        "MiroFish router: sending to swarm",
        endpoint=endpoint,
        swarm_id=resolved_swarm_id,
        num_agents=resolved_num_agents,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(endpoint, json=request_body)
            response.raise_for_status()
            result = response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.warning(
            "MiroFish router: request failed",
            endpoint=endpoint,
            error=str(exc),
        )
        record_translation_error(
            "mirofish",
            source_protocol or "unknown",
            "MIROFISH",
        )
        return {
            "status": "error",
            "error": "mirofish_request_failed",
            "detail": str(exc),
            "swarm_id": resolved_swarm_id,
            "endpoint": endpoint,
            "num_agents": resolved_num_agents,
        }

    logger.info(
        "MiroFish router: simulation response received",
        swarm_id=resolved_swarm_id,
        status=result.get("status", "unknown"),
    )

    return result
