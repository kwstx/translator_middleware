import asyncio
import structlog
import networkx as nx
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from app.core.translator import TranslatorEngine
from app.core.exceptions import HandoffRoutingError
from app.core.metrics import record_translation_error, record_translation_success
from app.services.mirofish_router import pipe_to_mirofish_swarm

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

    def handoff(
        self,
        source_message: Dict[str, Any],
        source_protocol: str,
        target_protocol: str,
    ) -> HandoffResult:
        """
        Perform a seamless (possibly multi-hop) protocol translation.

        1.  Use the ProtocolGraph to find the shortest path from
            *source_protocol* to *target_protocol*.
        2.  Walk the path, translating the message one hop at a time via
            TranslatorEngine.translate().
        3.  Return a HandoffResult with the final message, the route taken,
            and per-hop audit data.

        :param source_message:  The original message payload.
        :param source_protocol: Protocol the message currently conforms to.
        :param target_protocol: Protocol required by the receiving agent.
        :returns: HandoffResult with translated_message, route, total_weight,
                  and per-hop details.
        :raises HandoffRoutingError: If no path can be found.
        :raises TranslationError:    If any individual hop fails.
        """
        src = source_protocol.upper()
        tgt = target_protocol.upper()

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
        # MiroFish bridge — intercept when target platform is "MIROFISH".
        # The existing translation layer normalises the payload before
        # injection so semantic fidelity is preserved.  Users must first
        # launch their own MiroFish instance with their personal
        # LLM_API_KEY in its .env file.
        # -----------------------------------------------------------------
        if tgt == "MIROFISH":
            logger.info(
                "Handoff: routing to MiroFish swarm bridge",
                source_protocol=src,
            )
            if isinstance(source_message, dict):
                mirofish_meta = source_message.get("metadata", source_message.get("meta", {}))
                if not isinstance(mirofish_meta, dict):
                    mirofish_meta = {}
            else:
                mirofish_meta = {}

            swarm_id = mirofish_meta.get("swarmId")
            num_agents = mirofish_meta.get("numAgents")
            mirofish_base_url = mirofish_meta.get("mirofishBaseUrl")
            external_data = mirofish_meta.get("externalData")

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = loop.run_in_executor(
                            pool,
                            lambda: asyncio.run(
                                pipe_to_mirofish_swarm(
                                    message=source_message,
                                    external_data=external_data,
                                    swarm_id=swarm_id,
                                    num_agents=num_agents,
                                    mirofish_base_url=mirofish_base_url,
                                    source_protocol=src,
                                )
                            ),
                        )
                        import asyncio as _aio
                        mirofish_result = _aio.get_event_loop().run_until_complete(result)
                else:
                    mirofish_result = loop.run_until_complete(
                        pipe_to_mirofish_swarm(
                            message=source_message,
                            external_data=external_data,
                            swarm_id=swarm_id,
                            num_agents=num_agents,
                            mirofish_base_url=mirofish_base_url,
                            source_protocol=src,
                        )
                    )
            except RuntimeError:
                # Fallback: no running event loop
                mirofish_result = asyncio.run(
                    pipe_to_mirofish_swarm(
                        message=source_message,
                        external_data=external_data,
                        swarm_id=swarm_id,
                        num_agents=num_agents,
                        mirofish_base_url=mirofish_base_url,
                        source_protocol=src,
                    )
                )

            if isinstance(mirofish_result, dict) and mirofish_result.get("status") == "error":
                record_translation_error("orchestrator", src, "MIROFISH")
            else:
                record_translation_success("orchestrator", src, "MIROFISH")
            return HandoffResult(
                translated_message=mirofish_result,
                route=[src, "MIROFISH"],
                total_weight=0.0,
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
            current_message = self.translator.translate(
                current_message, hop_src, hop_tgt
            )

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
    ) -> HandoffResult:
        """Async variant of :meth:`handoff`.

        Preferred when calling from an ``async`` context (e.g. FastAPI
        route handlers).  Identical semantics to the synchronous version,
        but awaits the MiroFish bridge natively rather than blocking.
        """
        src = source_protocol.upper()
        tgt = target_protocol.upper()

        if tgt == "MIROFISH":
            logger.info(
                "Handoff async: routing to MiroFish swarm bridge",
                source_protocol=src,
            )
            if isinstance(source_message, dict):
                mirofish_meta = source_message.get("metadata", source_message.get("meta", {}))
                if not isinstance(mirofish_meta, dict):
                    mirofish_meta = {}
            else:
                mirofish_meta = {}

            mirofish_result = await pipe_to_mirofish_swarm(
                message=source_message,
                external_data=mirofish_meta.get("externalData"),
                swarm_id=mirofish_meta.get("swarmId"),
                num_agents=mirofish_meta.get("numAgents"),
                mirofish_base_url=mirofish_meta.get("mirofishBaseUrl"),
                source_protocol=src,
            )
            if isinstance(mirofish_result, dict) and mirofish_result.get("status") == "error":
                record_translation_error("orchestrator", src, "MIROFISH")
            else:
                record_translation_success("orchestrator", src, "MIROFISH")
            return HandoffResult(
                translated_message=mirofish_result,
                route=[src, "MIROFISH"],
                total_weight=0.0,
            )

        # Delegate standard handoff to the sync implementation
        return self.handoff(source_message, source_protocol, target_protocol)


if __name__ == "__main__":
    # Basic execution block for manual testing/running
    from app.core.logging import configure_logging
    configure_logging()
    orchestrator = Orchestrator()

