import asyncio
import structlog
import networkx as nx
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from app.core.translator import TranslatorEngine
from app.core.exceptions import HandoffRoutingError, HandoffAuthorizationError
from app.core.metrics import record_translation_error, record_translation_success, record_connector_call
from app.core.security import verify_engram_token
from app.messaging.connectors.registry import get_default_registry
from app.core.logging import bind_context
from app.core.execution_events import emit_execution_event
from app.messaging.intent_resolver import IntentResolver, IntentResolutionResult, AtomicTask

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data class for a single hop result in a multi-hop handoff
# ---------------------------------------------------------------------------
@dataclass
class HopResult:
    """Captures the outcome of a single translation hop."""
    source_protocol: str
    target_protocol: str
    message_snapshot: Dict[str, Any]
    weight: float  # edge cost used for this hop


@dataclass
class HandoffResult:
    """Full result of a multi-hop handoff, including the route taken."""
    translated_message: Dict[str, Any]
    route: List[str]             # e.g. ["A2A", "MCP", "ACP"]
    total_weight: float          # cumulative cost of the chosen path
    hops: List[HopResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ProtocolGraph — directed graph of protocol translation capabilities
# ---------------------------------------------------------------------------
class ProtocolGraph:
    """
    Models protocol translation capabilities as a weighted directed graph
    using NetworkX.  Each protocol is a node; each registered translator pair
    becomes a directed edge whose weight represents estimated fidelity cost
    (lower = better, default 1.0).

    The graph is used to find the **shortest path** (minimum cumulative weight)
    between any two protocols, enabling seamless multi-hop translations such as
    A2A → MCP → ACP even when no direct A2A → ACP translator exists.
    """

    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()

    # -- Graph construction -------------------------------------------------

    def add_protocol(self, protocol: str) -> None:
        """Register a protocol as a node (idempotent)."""
        self._graph.add_node(protocol.upper())

    def add_translation_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a directed edge representing a *direct* translation capability.

        :param source:   Source protocol name
        :param target:   Target protocol name
        :param weight:   Fidelity cost (lower is better).  Use values > 1 for
                         lossy translations to discourage their selection.
        :param metadata: Optional metadata dict stored on the edge (e.g.
                         translator version, data-loss warnings).
        """
        src, tgt = source.upper(), target.upper()
        self._graph.add_edge(src, tgt, weight=weight, meta=metadata or {})
        logger.debug(
            "ProtocolGraph edge added",
            source_protocol=src,
            target_protocol=tgt,
            weight=weight,
        )

    def build_from_translator(
        self,
        translator: TranslatorEngine,
        default_weight: float = 1.0,
    ) -> None:
        """
        Automatically populate the graph from a TranslatorEngine's registered
        mapper pairs so the graph always reflects the actual translation
        capabilities.
        """
        for src, tgt in translator.supported_pairs:
            self.add_translation_edge(src, tgt, weight=default_weight)
        logger.info(
            "ProtocolGraph built",
            node_count=self._graph.number_of_nodes(),
            edge_count=self._graph.number_of_edges(),
        )

    # -- Path-finding -------------------------------------------------------

    def find_shortest_path(
        self, source: str, target: str
    ) -> Tuple[List[str], float]:
        """
        Find the optimal (minimum-weight) sequence of protocol translations.

        :param source: Source protocol (e.g. "A2A")
        :param target: Target protocol (e.g. "ACP")
        :returns:      (path, total_weight) where path is e.g.
                       ["A2A", "MCP", "ACP"] and total_weight is the sum of
                       edge weights along that path.
        :raises HandoffRoutingError: If no path exists.
        """
        src, tgt = source.upper(), target.upper()

        if src not in self._graph:
            raise HandoffRoutingError(
                f"Source protocol '{src}' is not registered in the protocol graph"
            )
        if tgt not in self._graph:
            raise HandoffRoutingError(
                f"Target protocol '{tgt}' is not registered in the protocol graph"
            )

        try:
            path: List[str] = nx.shortest_path(
                self._graph, source=src, target=tgt, weight="weight"
            )
            total_weight: float = nx.shortest_path_length(
                self._graph, source=src, target=tgt, weight="weight"
            )
            return path, total_weight
        except nx.NetworkXNoPath:
            raise HandoffRoutingError(
                f"No translation route exists from '{src}' to '{tgt}'. "
                f"Available edges: {list(self._graph.edges)}"
            )

    # -- Introspection helpers ----------------------------------------------

    def has_direct_edge(self, source: str, target: str) -> bool:
        return self._graph.has_edge(source.upper(), target.upper())

    def get_all_protocols(self) -> List[str]:
        return list(self._graph.nodes)

    def get_all_edges(self) -> List[Tuple[str, str, float]]:
        return [
            (u, v, d.get("weight", 1.0))
            for u, v, d in self._graph.edges(data=True)
        ]

    def get_neighbors(self, protocol: str) -> List[str]:
        """Protocols directly reachable from the given protocol."""
        return list(self._graph.successors(protocol.upper()))

    def __repr__(self) -> str:
        return (
            f"ProtocolGraph(nodes={self.get_all_protocols()}, "
            f"edges={self.get_all_edges()})"
        )


# ---------------------------------------------------------------------------
# Orchestrator — extended with handoff support
# ---------------------------------------------------------------------------
class Orchestrator:
    """
    Orchestration engine for task handoffs using the translation graph.

    Core responsibilities:
      • **handoff()** — chain multiple translations along the shortest path
        in the ProtocolGraph for multi-hop collaborations (e.g. A2A → MCP → ACP).
    """

    def __init__(self):
        """
        Initializes the Orchestrator with a TranslatorEngine and ProtocolGraph.
        """
        self.translator = TranslatorEngine()
        self.protocol_graph = ProtocolGraph()

        # Build the graph from the translator's registered pairs
        self.protocol_graph.build_from_translator(self.translator)
        
        # NEW: Sophisticated Intent Resolution Layer
        self.intent_resolver = IntentResolver()
        
        # Initialize Tool Connectors
        self.connector_registry = get_default_registry()
        # Add connectors to the protocol graph so they can be discovered as valid targets
        for connector_name in self.connector_registry.list_connectors():
            self.protocol_graph.add_protocol(connector_name)

    # -- Graph management ---------------------------------------------------

    def register_translation_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Manually register an additional translation edge in the protocol
        graph.  Useful for adding edges discovered at runtime (e.g. when a
        new agent registers a novel translator).
        """
        self.protocol_graph.add_translation_edge(source, target, weight, metadata)

    # -- Multi-hop handoff --------------------------------------------------

    def _verify_eat_authorization(
        self,
        source_message: Dict[str, Any],
        source_protocol: str,
        target_protocol: str,
        eat: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts EAT from the message or explicit argument and validates that
        the user is authorized to perform this protocol handoff.
        """
        token = eat
        if not token and isinstance(source_message, dict):
            # Try extracting from message metadata
            meta = source_message.get("metadata", source_message.get("meta", {}))
            if isinstance(meta, dict):
                token = meta.get("eat") or meta.get("token") or meta.get("auth")

        if not token:
            # For backward compatibility or internal tasks, we might allow no token
            # but the policy says EVERY request must be authorized.
            # For now, we'll log a warning and let it pass if no token is provided, 
            # UNLESS a strict mode is enabled.
            # Wait, the prompt says "Ensures that every request... is authorized".
            # I'll be strict but I'll allow an 'X-Internal-Secret' or similar if needed for tests?
            # No, I'll just be strict and then I'll fix the tests.
            logger.warning("Handoff denied: No Engram Access Token (EAT) found.")
            raise HandoffAuthorizationError(
                "Missing Engram Access Token (EAT). All agent handoffs must be authorized."
            )

        try:
            payload = verify_engram_token(token)
            
            # Authorization check:
            # Does the EAT allow the 'translator' tool with the target protocol scope?
            src, tgt = source_protocol.upper(), target_protocol.upper()
            allowed_tools = [t.upper() for t in payload.get("allowed_tools", [])]
            permissions = payload.get("scopes", {}) # map tool_id -> list of scopes

            # 1. Broad 'translator' tool check
            if "TRANSLATOR" in allowed_tools:
                translator_scopes = permissions.get("translator", permissions.get("TRANSLATOR", []))
                if "*" in translator_scopes or tgt in translator_scopes or f"{src}:{tgt}" in translator_scopes:
                    return payload

            # 2. Specific tool check (e.g. tool "CLAUDE" or "SLACK" allowed)
            # Check for direct naming or case-insensitive match
            if tgt in allowed_tools:
                return payload
            
            # 3. Check within scopes keys (case-insensitive)
            permission_keys = [k.upper() for k in permissions.keys()]
            if tgt in permission_keys:
                return payload

            logger.error("Handoff unauthorized", user=payload.get("sub"), target=tgt)
            raise HandoffAuthorizationError(
                f"EAT for user '{payload.get('sub')}' does not authorize handoff to tool/protocol '{tgt}'."
            )

        except Exception as exc:
            if isinstance(exc, HandoffAuthorizationError):
                raise
            logger.error("EAT verification error", error=str(exc))
            raise HandoffAuthorizationError(f"EAT Verification failed: {str(exc)}")

    async def handoff(
        self,
        source_message: Dict[str, Any],
        source_protocol: str,
        target_protocol: str,
        eat: Optional[str] = None,
    ) -> HandoffResult:
        """
        Perform a seamless (possibly multi-hop) protocol translation.

        1.  Authorize the request via EAT (Engram Access Token).
        2.  Use the ProtocolGraph to find the shortest path from
            *source_protocol* to *target_protocol*.
        3.  Walk the path, translating the message one hop at a time via
            TranslatorEngine.translate().
        4.  Return a HandoffResult with the final message, the route taken,
            and per-hop audit data.

        :param source_message:  The original message payload.
        :param source_protocol: Protocol the message currently conforms to.
        :param target_protocol: Protocol required by the receiving agent.
        :param eat:             Optional explicit Engram Access Token (JWT).
        :returns: HandoffResult with translated_message, route, total_weight,
                  and per-hop details.
        :raises HandoffAuthorizationError: If the token is missing/invalid.
        :raises HandoffRoutingError: If no path can be found.
        :raises TranslationError:    If any individual hop fails.
        """
        src = source_protocol.upper()
        tgt = target_protocol.upper()

        # 1. Authorization
        auth_payload = self._verify_eat_authorization(
            source_message, src, tgt, eat
        )
        user_id = auth_payload.get("sub", "unknown")
        bind_context(user_id=user_id, source_protocol=src, target_protocol=tgt)

        logger.info(
            "Handoff authorized",
            user_id=user_id,
            source_protocol=src,
            target_protocol=tgt,
        )

        # Identity case — no translation needed
        if src == tgt:
            logger.info(
                "Handoff: source and target are identical; no-op",
                source_protocol=src,
                target_protocol=tgt,
            )
            record_translation_success("orchestrator", src, tgt)
            return HandoffResult(
                translated_message=source_message,
                route=[src],
                total_weight=0.0,
            )

        # -----------------------------------------------------------------
        # Tool Connectors — Check if target protocol is a registered tool.
        # This modular approach supports Claude, Slack, Perplexity, MiroFish etc.
        # -----------------------------------------------------------------
        if self.connector_registry.has_connector(tgt):
            logger.info("Handoff: routing to tool connector", target=tgt)
            connector = self.connector_registry.get_connector(tgt)
            
            # Since handoff is synchronous, we run the connector's execute in a new loop if needed,
            # but ideally connectors should be called via handoff_async.
            # For simplicity in this legacy method, we use asyncio.run or similar.
            start_time = time.time()
            try:
                # Basic sync-over-async
                import asyncio as _aio
                try:
                    loop = _aio.get_running_loop()
                    # If we are in a loop, we have to use a thread or similar
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        # Passing None for db here as sync session is tricky, but preferably we use handoff_async
                        future = loop.run_in_executor(pool, lambda: _aio.run(connector.execute(source_message, src, user_id=user_id)))
                        result = _aio.get_event_loop().run_until_complete(future)
                except RuntimeError:
                    result = _aio.run(connector.execute(source_message, src, user_id=user_id))
                
                record_connector_call(tgt, user_id, "success", time.time() - start_time)
                return HandoffResult(
                    translated_message=result,
                    route=[src, tgt],
                    total_weight=1.0, # Target reached
                )
            except Exception as e:
                logger.error("Connector execution failed in handoff", tool=tgt, error=str(e))
                record_connector_call(tgt, user_id, "error", time.time() - start_time)
                return HandoffResult(
                    translated_message={"status": "error", "detail": str(e)},
                    route=[src, tgt],
                    total_weight=1.0
                )

        # Find the optimal route
        path, total_weight = self.protocol_graph.find_shortest_path(src, tgt)
        logger.info(
            "Handoff route",
            route=" -> ".join(path),
            total_weight=total_weight,
        )

        # Chain translations along the path
        current_message = source_message
        hops: List[HopResult] = []

        for i in range(len(path) - 1):
            hop_src = path[i]
            hop_tgt = path[i + 1]

            edge_data = self.protocol_graph._graph.edges[hop_src, hop_tgt]
            hop_weight = edge_data.get("weight", 1.0)

            logger.info(
                "Handoff hop",
                hop_index=i + 1,
                hop_total=len(path) - 1,
                source_protocol=hop_src,
                target_protocol=hop_tgt,
            )
            try:
                # NEW: Emit debug events for translation
                task_id = source_message.get("metadata", {}).get("task_id")
                
                await emit_execution_event(
                    "translation.engram",
                    f"🔄 [magenta]Hop {i+1}:[/] Translating {hop_src} to {hop_tgt}",
                    task_id=task_id,
                    db=None, # Usually called from sync context or we don't have db here
                    data={"payload": current_message, "connector": f"{hop_src}->{hop_tgt}", "step": i+1}
                )

                current_message = self.translator.translate(
                    current_message, hop_src, hop_tgt
                )

                await emit_execution_event(
                    "translation.request",
                    f"✨ [green]Hop {i+1} OK:[/] Resulting {hop_tgt} payload generated.",
                    task_id=task_id,
                    db=None,
                    data={"payload": current_message, "connector": f"{hop_src}->{hop_tgt}", "step": i+1}
                )

                record_translation_success("orchestrator", hop_src, hop_tgt)
            except Exception as e:
                logger.error("Translation hop failed", source_protocol=hop_src, target_protocol=hop_tgt, error=str(e))
                record_translation_error("orchestrator", hop_src, hop_tgt)
                raise

            hops.append(
                HopResult(
                    source_protocol=hop_src,
                    target_protocol=hop_tgt,
                    message_snapshot=current_message.copy(),
                    weight=hop_weight,
                )
            )

        return HandoffResult(
            translated_message=current_message,
            route=path,
            total_weight=total_weight,
            hops=hops,
        )

    async def handoff_async(
        self,
        source_message: Dict[str, Any],
        source_protocol: str,
        target_protocol: str,
        eat: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> HandoffResult:
        """Async variant of :meth:`handoff`.

        Preferred when calling from an ``async`` context (e.g. FastAPI
        route handlers).  Identical semantics to the synchronous version,
        but awaits the MiroFish bridge natively rather than blocking.
        """
        src = source_protocol.upper()
        tgt = target_protocol.upper()

        # Authorization is handled inside handoff() but we need to pass the eat
        # 1. Authorization is handled inside _verify_eat_authorization
        # (We call it here because we intercept the tool routing)
        if self.connector_registry.has_connector(tgt):
            auth_payload = self._verify_eat_authorization(source_message, src, tgt, eat)
            user_id = auth_payload.get("sub", "unknown")
            bind_context(user_id=user_id, source_protocol=src, target_protocol=tgt)
            
            logger.info("Handoff async authorized for tool", tool=tgt, user_id=user_id)
            
            connector = self.connector_registry.get_connector(tgt)
            # Inject user_id into message metadata for the connector to find if db is not passed? 
            # Better to pass db directly to execute.
            start_time = time.time()
            try:
                result = await connector.execute(source_message, src, db=db, user_id=user_id)
                record_connector_call(tgt, user_id, "success", time.time() - start_time)
                return HandoffResult(
                    translated_message=result,
                    route=[src, tgt],
                    total_weight=0.0,
                )
            except Exception as e:
                logger.error("Connector execution failed in handoff_async", tool=tgt, error=str(e))
                record_connector_call(tgt, user_id, "error", time.time() - start_time)
                return HandoffResult(
                    translated_message={"status": "error", "error": str(e)},
                    route=[src, tgt],
                    total_weight=0.0
                )

        # NEW: If source_protocol is NL, we first resolve the complex intent
        # to decompose into atomic tasks before standard handoff.
        if src == "NL":
            logger.info("Decomposing NL command into atomic tasks.", prompt=source_message.get("command"))
            resolution: IntentResolutionResult = await self.intent_resolver.resolve(
                source_message.get("command", ""), db=db
            )
            
            if resolution.tasks:
                # We'll handle the first task for now in this handoff_async call
                # But could also queue multiple tasks or handle them sequentially
                primary_task: AtomicTask = resolution.tasks[0]
                logger.info(
                    "Primary task extracted", 
                    intent=primary_task.intent, 
                    capability=primary_task.capability_tag, 
                    params=primary_task.parameters
                )
                
                # Strip ambient language from payload and update with extracted params
                # This prevents "downstream payload pollution"
                new_payload = {
                     "intent": primary_task.intent,
                     "capability_tag": primary_task.capability_tag,
                     **primary_task.parameters
                }
                
                # Check for metadata/context from original message
                if "metadata" in source_message:
                     new_payload["metadata"] = source_message["metadata"]
                
                # Route based on the extracted intent and target protocol
                # If target protocol is not specified, we can try to guess from the task
                resolved_target = target_protocol
                if not resolved_target or resolved_target == "AUTO":
                    # Simple heuristic: 'predict' -> MiroFish
                    if primary_task.intent == "predict":
                        resolved_target = "MIROFISH"
                    else:
                        resolved_target = "MCP" # Default bridging protocol
                
                return await self.handoff(new_payload, "NL", resolved_target, eat)
            
        # Delegate standard handoff to the sync implementation
        return await self.handoff(source_message, source_protocol, target_protocol, eat)


if __name__ == "__main__":
    # Basic execution block for manual testing/running
    from app.core.logging import configure_logging
    configure_logging()
    orchestrator = Orchestrator()

