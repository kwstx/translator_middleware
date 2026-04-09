import structlog
import networkx as nx
import time
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.translator import TranslatorEngine
from app.core.exceptions import HandoffRoutingError, HandoffAuthorizationError
from app.core.metrics import (
    record_translation_error, 
    record_translation_success, 
    record_connector_call
)
from app.core import security
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
    proof: Optional[str] = None # Cryptographic hash of the hop execution

@dataclass
class HandoffResult:
    """Full result of a multi-hop handoff, including the route taken."""
    translated_message: Dict[str, Any]
    route: List[str]             # e.g. ["A2A", "MCP", "ACP"]
    total_weight: float          # cumulative cost of the chosen path
    proof: Optional[str] = None  # Full path verification proof
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
    """

    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()

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
        src, tgt = source.upper(), target.upper()
        self._graph.add_edge(src, tgt, weight=weight, meta=metadata or {})
        logger.debug("ProtocolGraph edge added", source=src, target=tgt, weight=weight)

    def build_from_translator(self, translator: TranslatorEngine, default_weight: float = 1.0) -> None:
        for src, tgt in translator.supported_pairs:
            self.add_translation_edge(src, tgt, weight=default_weight)

    async def build_from_registry(self, session: AsyncSession) -> None:
        """Populates the graph with dynamic weights from the database."""
        from sqlmodel import select
        from app.db.models import AgentRegistry, ProtocolMapping

        mappings = (await session.execute(select(ProtocolMapping))).scalars().all()
        agents = (await session.execute(select(AgentRegistry).where(AgentRegistry.is_active == True))).scalars().all()

        for m in mappings:
            src, tgt = m.source_protocol.upper(), m.target_protocol.upper()
            self._graph.add_node(src)
            self._graph.add_node(tgt)
            self.add_translation_edge(src, tgt, weight=m.fidelity_weight)

        for agent in agents:
            # For each protocol the agent supports, add an edge from that protocol to the agent endpoint
            agent_node = agent.endpoint_url.upper()
            self._graph.add_node(agent_node, type="agent")
            
            for protocol in agent.supported_protocols:
                p_node = protocol.upper()
                self._graph.add_node(p_node, type="protocol")
                
                # Dynamic weight formula
                # Base = 1.0
                # Latency penalty: 0.1 per second of avg_latency
                latency_penalty = agent.avg_latency * 0.1
                # Reliability penalty: 5.0 penalty for every 10% below 100% success
                reliability_penalty = (1.0 - agent.success_rate) * 50.0
                
                total_weight = 1.0 + latency_penalty + reliability_penalty
                self._graph.add_edge(p_node, agent_node, weight=total_weight, agent_id=agent.agent_id)

    def find_shortest_path(self, source: str, target: str) -> Tuple[List[str], float]:
        src, tgt = source.upper(), target.upper()
        if src not in self._graph:
            raise HandoffRoutingError(f"Source protocol '{src}' is not registered.")
        if tgt not in self._graph:
            # Check if target matches any agent by endpoint or similar? 
            # Or perhaps just raise error if target is not a node.
            raise HandoffRoutingError(f"Target '{tgt}' is not registered.")

        try:
            path = nx.shortest_path(self._graph, source=src, target=tgt, weight="weight")
            total_weight = nx.shortest_path_length(self._graph, source=src, target=tgt, weight="weight")
            return path, total_weight
        except nx.NetworkXNoPath:
            raise HandoffRoutingError(f"No translation route from '{src}' to '{tgt}'.")

    def has_direct_edge(self, source: str, target: str) -> bool:
        return self._graph.has_edge(source.upper(), target.upper())
    def get_all_protocols(self) -> List[str]:
        return list(self._graph.nodes)
    def get_all_edges(self) -> List[Tuple[str, str, float]]:
        return [(u, v, d.get("weight", 1.0)) for u, v, d in self._graph.edges(data=True)]
    def get_neighbors(self, protocol: str) -> List[str]:
        return list(self._graph.successors(protocol.upper()))
    def __repr__(self) -> str:
        return f"ProtocolGraph(nodes={self.get_all_protocols()}, edges={self.get_all_edges()})"

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Orchestrator:
    def __init__(self):
        self._translator = None
        self._protocol_graph = None
        self._intent_resolver = None
        self._connector_registry = None

    @property
    def translator(self) -> TranslatorEngine:
        if self._translator is None:
            self._translator = TranslatorEngine()
        return self._translator

    @property
    def protocol_graph(self) -> ProtocolGraph:
        if self._protocol_graph is None:
            self._protocol_graph = ProtocolGraph()
            self._protocol_graph.build_from_translator(self.translator)
            for c in self.connector_registry.list_connectors():
                self._protocol_graph.add_protocol(c)
        return self._protocol_graph

    @property
    def intent_resolver(self) -> IntentResolver:
        if self._intent_resolver is None:
            self._intent_resolver = IntentResolver()
        return self._intent_resolver

    @property
    def connector_registry(self):
        if self._connector_registry is None:
            self._connector_registry = get_default_registry()
        return self._connector_registry

    def _generate_execution_proof(self, source_protocol: str, target_protocol: str, input_payload: Dict[str, Any], output_payload: Dict[str, Any]) -> str:
        """Generates a verifiable proof of execution for a single hop."""
        payload_hash = hashlib.sha256(json.dumps({
            "in": input_payload,
            "out": output_payload,
            "src": source_protocol.upper(),
            "tgt": target_protocol.upper(),
            "ts": datetime.now(timezone.utc).isoformat()
        }, sort_keys=True).encode()).hexdigest()
        return f"v1:sha256:{payload_hash}"

    def register_translation_edge(self, source: str, target: str, weight: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.protocol_graph.add_translation_edge(source, target, weight, metadata)

    def _verify_eat_authorization(self, source_message: Dict[str, Any], source_protocol: str, target_protocol: str, eat: Optional[str] = None) -> Dict[str, Any]:
        token = eat
        if not token and isinstance(source_message, dict):
            meta = source_message.get("metadata", source_message.get("meta", {}))
            if isinstance(meta, dict):
                token = meta.get("eat") or meta.get("token") or meta.get("auth")
        if not token:
            logger.warning("Handoff denied: No Engram Access Token (EAT) found.")
            raise HandoffAuthorizationError("Missing Engram Access Token (EAT).")
        try:
            payload = verify_engram_token(token)
            src, tgt = source_protocol.upper(), target_protocol.upper()
            allowed_tools = [t.upper() for t in payload.get("allowed_tools", [])]
            permissions = payload.get("scopes", {})
            if "TRANSLATOR" in allowed_tools:
                translator_scopes = permissions.get("translator", permissions.get("TRANSLATOR", []))
                if "*" in translator_scopes or tgt in translator_scopes or f"{src}:{tgt}" in translator_scopes:
                    return payload
            if tgt in allowed_tools or tgt in [k.upper() for k in permissions.keys()]:
                return payload
            raise HandoffAuthorizationError(f"EAT does not authorize handoff to tool/protocol '{tgt}'.")
        except Exception as e:
            if isinstance(e, HandoffAuthorizationError): raise
            raise HandoffAuthorizationError(f"EAT Verification failed: {str(e)}")

    async def handoff(self, source_message: Dict[str, Any], source_protocol: str, target_protocol: str, eat: Optional[str] = None) -> HandoffResult:
        src, tgt = source_protocol.upper(), target_protocol.upper()
        auth_payload = self._verify_eat_authorization(source_message, src, tgt, eat)
        user_id = auth_payload.get("sub", "unknown")
        bind_context(user_id=user_id, source_protocol=src, target_protocol=tgt)

        if src == tgt:
            record_translation_success("orchestrator", src, tgt)
            return HandoffResult(translated_message=source_message, route=[src], total_weight=0.0)

        # Tool Connectors
        if self.connector_registry.has_connector(tgt):
            connector = self.connector_registry.get_connector(tgt)
            start_time = time.time()
            try:
                import asyncio as _aio
                try:
                    loop = _aio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = loop.run_in_executor(pool, lambda: _aio.run(connector.execute(source_message, src, user_id=user_id)))
                        result = await future
                except RuntimeError:
                    result = _aio.run(connector.execute(source_message, src, user_id=user_id))
                record_connector_call(tgt, user_id, "success", time.time() - start_time)
                return HandoffResult(translated_message=result, route=[src, tgt], total_weight=1.0)
            except Exception as e:
                record_connector_call(tgt, user_id, "error", time.time() - start_time)
                return HandoffResult(translated_message={"status": "error", "detail": str(e)}, route=[src, tgt], total_weight=1.0)

        path, total_weight = self.protocol_graph.find_shortest_path(src, tgt)
        current_message = source_message
        hops = []
        for i in range(len(path) - 1):
            hop_src, hop_tgt = path[i], path[i+1]
            hop_input = current_message.copy()
            hop_weight = self.protocol_graph._graph.edges[hop_src, hop_tgt].get("weight", 1.0)
            try:
                task_id = source_message.get("metadata", {}).get("task_id")
                await emit_execution_event("translation.engram", f"🔄 Hop {i+1}: Translating {hop_src} to {hop_tgt}", task_id=task_id, data={"payload": current_message})
                current_message = self.translator.translate(current_message, hop_src, hop_tgt)
                await emit_execution_event("translation.request", f"✨ Hop {i+1} OK: {hop_tgt} generated.", task_id=task_id, data={"payload": current_message})
                record_translation_success("orchestrator", hop_src, hop_tgt)
            except Exception as e:
                record_translation_error("orchestrator", hop_src, hop_tgt)
                raise
            
            # Generate proof for this hop
            hop_proof = self._generate_execution_proof(hop_src, hop_tgt, hop_input, current_message)
            hops.append(HopResult(
                source_protocol=hop_src, 
                target_protocol=hop_tgt, 
                message_snapshot=current_message.copy(), 
                weight=hop_weight,
                proof=hop_proof
            ))
        
        # Calculate aggregate proof
        aggregate_proof = hashlib.sha256(("".join([h.proof or "" for h in hops])).encode()).hexdigest() if hops else "N/A"
        return HandoffResult(
            translated_message=current_message, 
            route=path, 
            total_weight=total_weight, 
            hops=hops,
            proof=f"v1:agg:{aggregate_proof}"
        )

    async def handoff_async(self, source_message: Dict[str, Any], source_protocol: str, target_protocol: str, eat: Optional[str] = None, db: Optional[Any] = None) -> HandoffResult:
        src, tgt = source_protocol.upper(), target_protocol.upper()
        if db:
            await self.protocol_graph.build_from_registry(db)

        if self.connector_registry.has_connector(tgt):
            auth_payload = self._verify_eat_authorization(source_message, src, tgt, eat)
            user_id = auth_payload.get("sub", "unknown")
            connector = self.connector_registry.get_connector(tgt)
            start_time = time.time()
            try:
                result = await connector.execute(source_message, src, db=db, user_id=user_id)
                record_connector_call(tgt, user_id, "success", time.time() - start_time)
                return HandoffResult(translated_message=result, route=[src, tgt], total_weight=0.0)
            except Exception as e:
                record_connector_call(tgt, user_id, "error", time.time() - start_time)
                return HandoffResult(translated_message={"status": "error", "error": str(e)}, route=[src, tgt], total_weight=0.0)

        if src == "NL":
            resolution = await self.intent_resolver.resolve(source_message.get("command", ""), db=db)
            if resolution.tasks:
                primary = resolution.tasks[0]
                new_payload = {"intent": primary.intent, "capability_tag": primary.capability_tag, **primary.parameters}
                if "metadata" in source_message: new_payload["metadata"] = source_message["metadata"]
                resolved_target = target_protocol
                if not resolved_target or resolved_target == "AUTO":
                    resolved_target = "MCP"
                return await self.handoff(new_payload, "NL", resolved_target, eat)

        return await self.handoff(source_message, source_protocol, target_protocol, eat)


if __name__ == "__main__":
    from app.core.logging import configure_logging
    configure_logging()
    orchestrator = Orchestrator()
