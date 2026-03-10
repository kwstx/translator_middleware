import pika
import json
import logging
import networkx as nx
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from app.core.config import settings
from app.core.translator import TranslatorEngine
from app.core.exceptions import HandoffRoutingError

logger = logging.getLogger(__name__)


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
        logger.debug(f"ProtocolGraph edge added: {src} → {tgt} (w={weight})")

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
            f"ProtocolGraph built with {self._graph.number_of_nodes()} nodes, "
            f"{self._graph.number_of_edges()} edges"
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
    Orchestration engine for task handoffs using RabbitMQ.

    Core responsibilities:
      • Listen on incoming queues, translate messages via TranslatorEngine,
        and forward them to agent-specific queues.
      • **handoff()** — chain multiple translations along the shortest path
        in the ProtocolGraph for multi-hop collaborations (e.g. A2A → MCP → ACP).
    """

    def __init__(self, amqp_url: Optional[str] = None):
        """
        Initializes the Orchestrator with a RabbitMQ connection URL,
        TranslatorEngine, and ProtocolGraph.
        """
        self.amqp_url = amqp_url or settings.RABBIT_URL
        self.translator = TranslatorEngine()
        self.protocol_graph = ProtocolGraph()
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

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
            logger.info(f"Handoff: source and target are both '{src}'; no-op")
            return HandoffResult(
                translated_message=source_message,
                route=[src],
                total_weight=0.0,
            )

        # Find the optimal route
        path, total_weight = self.protocol_graph.find_shortest_path(src, tgt)
        logger.info(
            f"Handoff route: {' → '.join(path)} (total weight: {total_weight})"
        )

        # Chain translations along the path
        current_message = source_message
        hops: List[HopResult] = []

        for i in range(len(path) - 1):
            hop_src = path[i]
            hop_tgt = path[i + 1]

            edge_data = self.protocol_graph._graph.edges[hop_src, hop_tgt]
            hop_weight = edge_data.get("weight", 1.0)

            logger.info(f"  Hop {i + 1}/{len(path) - 1}: {hop_src} → {hop_tgt}")
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

    # -- RabbitMQ connection management  ------------------------------------

    def _connect(self):
        """
        Establishes a blocking connection and channel if not already connected.
        """
        if not self._connection or self._connection.is_closed:
            try:
                parameters = pika.URLParameters(self.amqp_url)
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                logger.info(f"Successfully connected to RabbitMQ at {self.amqp_url}")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
                raise

    def publish_translated(self, target_agent_id: str, message: Dict[str, Any]):
        """
        Publishes a translated message to a queue named 'agent-<uuid>-queue'.
        Uses persistent delivery mode to prevent message loss.
        """
        self._connect()
        queue_name = f"agent-{target_agent_id}-queue"

        # Ensure the target queue exists and is durable
        self._channel.queue_declare(queue=queue_name, durable=True)

        self._channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message, default=str),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
        logger.info(f"Published translated message to {queue_name}")

    def consume(self, incoming_queue: str = "incoming_tasks"):
        """
        Listens on a general incoming queue, translates via multi-hop handoff,
        and forwards messages.  Implements manual acknowledgments for
        reliability.
        """
        self._connect()
        self._channel.queue_declare(queue=incoming_queue, durable=True)

        # Fair dispatch: process one message at a time
        self._channel.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):
            logger.info(f"Received raw message from {incoming_queue}")
            try:
                payload = json.loads(body.decode())

                # Expected payload structure:
                # {
                #   "source_message": {...},
                #   "source_protocol": "A2A",
                #   "target_protocol": "MCP",
                #   "target_agent_id": "uuid-..."
                # }

                source_message = payload.get("source_message")
                source_protocol = payload.get("source_protocol")
                target_protocol = payload.get("target_protocol")
                target_agent_id = payload.get("target_agent_id")

                if not all([source_message, source_protocol, target_protocol, target_agent_id]):
                    logger.warning("Message dropped: Missing required fields (source_message, protocols, or target_agent_id)")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                # Use multi-hop handoff (handles direct & chained translations)
                result = self.handoff(source_message, source_protocol, target_protocol)
                logger.info(f"Handoff complete via route: {' → '.join(result.route)}")

                # Forward the translated message to the target agent
                self.publish_translated(target_agent_id, result.translated_message)

                # Acknowledge receipt after successful forwarding
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Successfully processed and forwarded message for agent {target_agent_id}")

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Nack message. Don't requeue if it's a permanent translation error to avoid infinite loops.
                # In production, this should go to a Dead Letter Queue (DLQ).
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self._channel.basic_consume(queue=incoming_queue, on_message_callback=callback)
        logger.info(f"Orchestrator started. Listening on queue: {incoming_queue}")
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Orchestrator stopping...")
            self.close()

    def close(self):
        """
        Closes the RabbitMQ connection.
        """
        if self._connection and self._connection.is_open:
            self._connection.close()
            logger.info("RabbitMQ connection closed.")


if __name__ == "__main__":
    # Basic execution block for manual testing/running
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    orchestrator = Orchestrator()
    try:
        orchestrator.consume()
    except Exception as exc:
        logger.critical(f"Orchestrator fatal error: {exc}")

