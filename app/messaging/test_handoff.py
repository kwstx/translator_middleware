"""
Tests for the ProtocolGraph and Orchestrator.handoff() multi-hop routing.

Run with:
    python -m pytest app/messaging/test_handoff.py -v
"""
import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so we can import without a live RabbitMQ / Postgres
# ---------------------------------------------------------------------------
# Patch pika before importing the orchestrator
import types

_pika_stub = types.ModuleType("pika")
_pika_stub.BlockingConnection = type("BlockingConnection", (), {})
_pika_stub.URLParameters = lambda url: url
_pika_stub.BasicProperties = lambda **kw: None

_blocking_mod = types.ModuleType("pika.adapters.blocking_connection")
_blocking_mod.BlockingChannel = type("BlockingChannel", (), {})
_pika_stub.adapters = types.ModuleType("pika.adapters")
_pika_stub.adapters.blocking_connection = _blocking_mod

sys.modules.setdefault("pika", _pika_stub)
sys.modules.setdefault("pika.adapters", _pika_stub.adapters)
sys.modules.setdefault("pika.adapters.blocking_connection", _blocking_mod)

# Patch settings so we don't need a .env / database
_config_mod = types.ModuleType("app.core.config")

class _FakeSettings:
    RABBIT_URL = "amqp://guest:guest@localhost:5672/"

_config_mod.settings = _FakeSettings()
sys.modules["app.core.config"] = _config_mod

# ---------------------------------------------------------------------------
# Now we can safely import
# ---------------------------------------------------------------------------
from app.core.translator import TranslatorEngine
from app.core.exceptions import HandoffRoutingError
from app.messaging.orchestrator import ProtocolGraph, Orchestrator, HandoffResult


# ===================================================================
# ProtocolGraph unit tests
# ===================================================================

class TestProtocolGraph:
    """Tests for the standalone ProtocolGraph."""

    def test_add_protocol_and_edge(self):
        g = ProtocolGraph()
        g.add_protocol("A2A")
        g.add_protocol("MCP")
        g.add_translation_edge("A2A", "MCP", weight=1.0)

        assert g.has_direct_edge("A2A", "MCP")
        assert not g.has_direct_edge("MCP", "A2A")  # directed

    def test_build_from_translator(self):
        engine = TranslatorEngine()
        g = ProtocolGraph()
        g.build_from_translator(engine)

        # The engine has ("A2A", "MCP") registered
        assert g.has_direct_edge("A2A", "MCP")
        assert "A2A" in g.get_all_protocols()
        assert "MCP" in g.get_all_protocols()

    def test_shortest_path_direct(self):
        g = ProtocolGraph()
        g.add_translation_edge("A2A", "MCP", weight=1.0)

        path, weight = g.find_shortest_path("A2A", "MCP")
        assert path == ["A2A", "MCP"]
        assert weight == 1.0

    def test_shortest_path_multi_hop(self):
        g = ProtocolGraph()
        g.add_translation_edge("A2A", "MCP", weight=1.0)
        g.add_translation_edge("MCP", "ACP", weight=1.0)

        path, weight = g.find_shortest_path("A2A", "ACP")
        assert path == ["A2A", "MCP", "ACP"]
        assert weight == 2.0

    def test_shortest_path_prefers_lower_weight(self):
        """When a direct but lossy edge exists, the graph should still
        prefer the cheaper multi-hop route."""
        g = ProtocolGraph()
        # Direct route: A2A -> ACP with high cost (lossy)
        g.add_translation_edge("A2A", "ACP", weight=10.0)
        # Multi-hop route: A2A -> MCP -> ACP with lower total cost
        g.add_translation_edge("A2A", "MCP", weight=1.0)
        g.add_translation_edge("MCP", "ACP", weight=1.0)

        path, weight = g.find_shortest_path("A2A", "ACP")
        assert path == ["A2A", "MCP", "ACP"]
        assert weight == 2.0

    def test_no_path_raises(self):
        g = ProtocolGraph()
        g.add_protocol("A2A")
        g.add_protocol("XYZ")

        with pytest.raises(HandoffRoutingError, match="No translation route"):
            g.find_shortest_path("A2A", "XYZ")

    def test_unknown_source_raises(self):
        g = ProtocolGraph()
        g.add_protocol("MCP")

        with pytest.raises(HandoffRoutingError, match="Source protocol"):
            g.find_shortest_path("UNKNOWN", "MCP")

    def test_unknown_target_raises(self):
        g = ProtocolGraph()
        g.add_protocol("MCP")

        with pytest.raises(HandoffRoutingError, match="Target protocol"):
            g.find_shortest_path("MCP", "UNKNOWN")

    def test_get_neighbors(self):
        g = ProtocolGraph()
        g.add_translation_edge("A2A", "MCP")
        g.add_translation_edge("A2A", "ACP")

        neighbors = g.get_neighbors("A2A")
        assert set(neighbors) == {"MCP", "ACP"}

    def test_case_insensitivity(self):
        g = ProtocolGraph()
        g.add_translation_edge("a2a", "mcp")
        assert g.has_direct_edge("A2A", "MCP")

    def test_repr(self):
        g = ProtocolGraph()
        g.add_translation_edge("A2A", "MCP")
        txt = repr(g)
        assert "A2A" in txt
        assert "MCP" in txt


# ===================================================================
# Orchestrator.handoff() integration tests
# ===================================================================

class TestOrchestratorHandoff:
    """Tests for the Orchestrator's handoff method."""

    def _make_orchestrator(self) -> Orchestrator:
        """Create an Orchestrator without a live RabbitMQ connection."""
        orch = Orchestrator.__new__(Orchestrator)
        orch.amqp_url = "amqp://localhost"
        orch.translator = TranslatorEngine()
        orch.protocol_graph = ProtocolGraph()
        orch.protocol_graph.build_from_translator(orch.translator)
        orch._connection = None
        orch._channel = None
        return orch

    def test_identity_handoff(self):
        """Same protocol → no translation needed."""
        orch = self._make_orchestrator()
        msg = {"payload": {"value": 42}}

        result = orch.handoff(msg, "A2A", "A2A")
        assert result.translated_message == msg
        assert result.route == ["A2A"]
        assert result.total_weight == 0.0
        assert result.hops == []

    def test_direct_handoff_a2a_to_mcp(self):
        """Direct A2A → MCP translation via single hop."""
        orch = self._make_orchestrator()
        msg = {"payload": {"action": "test"}, "id": "001"}

        result = orch.handoff(msg, "A2A", "MCP")
        assert result.route == ["A2A", "MCP"]
        assert result.total_weight == 1.0
        assert len(result.hops) == 1
        # "payload" should be transformed to "data_bundle"
        assert "data_bundle" in result.translated_message
        assert "payload" not in result.translated_message

    def test_multi_hop_handoff(self):
        """A2A → MCP → ACP multi-hop chain."""
        orch = self._make_orchestrator()

        # Register a stub MCP → ACP translator
        def mcp_to_acp(message):
            translated = {}
            for k, v in message.items():
                new_key = "acp_content" if k == "data_bundle" else k
                translated[new_key] = v
            return translated

        orch.translator._mappers[("MCP", "ACP")] = mcp_to_acp
        orch.protocol_graph.add_translation_edge("MCP", "ACP", weight=1.5)

        msg = {"payload": {"task": "collaborate"}, "session": "s01"}
        result = orch.handoff(msg, "A2A", "ACP")

        assert result.route == ["A2A", "MCP", "ACP"]
        assert result.total_weight == 2.5  # 1.0 + 1.5
        assert len(result.hops) == 2
        # Final message should have gone through both transforms
        assert "acp_content" in result.translated_message
        assert "payload" not in result.translated_message
        assert "data_bundle" not in result.translated_message

    def test_handoff_no_route_raises(self):
        """HandoffRoutingError when no route exists."""
        orch = self._make_orchestrator()
        orch.protocol_graph.add_protocol("XYZ")

        with pytest.raises(HandoffRoutingError):
            orch.handoff({"data": 1}, "MCP", "XYZ")

    def test_register_edge_at_runtime(self):
        """Edges added via register_translation_edge() are discovered."""
        orch = self._make_orchestrator()

        def identity(m):
            return m

        orch.translator._mappers[("MCP", "ACP")] = identity
        orch.register_translation_edge("MCP", "ACP", weight=0.5)

        path, w = orch.protocol_graph.find_shortest_path("A2A", "ACP")
        assert path == ["A2A", "MCP", "ACP"]
        assert w == 1.5  # 1.0 + 0.5

    def test_handoff_prefers_optimal_route(self):
        """When multiple routes exist, handoff uses the lowest-weight path."""
        orch = self._make_orchestrator()

        # Direct A2A → ACP: expensive (lossy)
        def lossy(m):
            return {"lossy": True}

        orch.translator._mappers[("A2A", "ACP")] = lossy
        orch.protocol_graph.add_translation_edge("A2A", "ACP", weight=10.0)

        # Multi-hop: A2A → MCP → ACP: cheap
        def mcp_to_acp(m):
            return {**m, "via_mcp": True}

        orch.translator._mappers[("MCP", "ACP")] = mcp_to_acp
        orch.protocol_graph.add_translation_edge("MCP", "ACP", weight=1.0)

        result = orch.handoff({"payload": {"x": 1}}, "A2A", "ACP")
        # Should pick the 2-hop route (cost 2.0) over direct (cost 10.0)
        assert result.route == ["A2A", "MCP", "ACP"]
        assert result.total_weight == 2.0
        assert result.translated_message.get("via_mcp") is True

    def test_hop_results_contain_snapshots(self):
        """Each HopResult must contain a snapshot of the message at that stage."""
        orch = self._make_orchestrator()

        def mcp_to_acp(m):
            return {"final": True}

        orch.translator._mappers[("MCP", "ACP")] = mcp_to_acp
        orch.protocol_graph.add_translation_edge("MCP", "ACP")

        result = orch.handoff({"payload": {"step": 1}}, "A2A", "ACP")

        hop1 = result.hops[0]
        assert hop1.source_protocol == "A2A"
        assert hop1.target_protocol == "MCP"
        assert "data_bundle" in hop1.message_snapshot

        hop2 = result.hops[1]
        assert hop2.source_protocol == "MCP"
        assert hop2.target_protocol == "ACP"
        assert hop2.message_snapshot == {"final": True}


# ===================================================================
# Run
# ===================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
