"""
Tests for the ProtocolGraph and Orchestrator.handoff() multi-hop routing.

Run with:
    python -m pytest app/messaging/test_handoff.py -v
"""
import pytest
from app.core.translator import TranslatorEngine
from app.core.exceptions import HandoffRoutingError, HandoffAuthorizationError
from app.messaging.orchestrator import ProtocolGraph, Orchestrator, HandoffResult
from app.core.security import create_engram_access_token
from app.core.config import settings

# Setup a dummy secret for testing
settings.AUTH_JWT_SECRET = "test-secret-key-12345"

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


# ===================================================================
# Orchestrator.handoff() integration tests
# ===================================================================

class TestOrchestratorHandoff:
    """Tests for the Orchestrator's handoff method."""

    def _make_orchestrator(self) -> Orchestrator:
        """Create an Orchestrator without external dependencies."""
        orch = Orchestrator.__new__(Orchestrator)
        orch.translator = TranslatorEngine()
        orch.protocol_graph = ProtocolGraph()
        orch.protocol_graph.build_from_translator(orch.translator)
        return orch

    def _get_test_token(self, tool_permissions: dict = None) -> str:
        """Helper to generate a valid EAT for tests."""
        perms = tool_permissions or {"translator": ["*"]}
        return create_engram_access_token(user_id="test-user", permissions=perms)

    def test_identity_handoff(self):
        """Same protocol → no translation needed."""
        orch = self._make_orchestrator()
        msg = {"payload": {"value": 42}}
        token = self._get_test_token()

        result = orch.handoff(msg, "A2A", "A2A", eat=token)
        assert result.translated_message == msg
        assert result.route == ["A2A"]
        assert result.total_weight == 0.0
        assert result.hops == []

    def test_handoff_no_token_raises(self):
        """Handoff should raise AuthorizationError if no token is provided."""
        orch = self._make_orchestrator()
        with pytest.raises(HandoffAuthorizationError, match="Missing Engram Access Token"):
            orch.handoff({"p": 1}, "A2A", "MCP")

    def test_direct_handoff_a2a_to_mcp(self):
        """Direct A2A → MCP translation via single hop."""
        orch = self._make_orchestrator()
        msg = {"payload": {"action": "test"}, "id": "001"}
        token = self._get_test_token()

        result = orch.handoff(msg, "A2A", "MCP", eat=token)
        assert result.route == ["A2A", "MCP"]
        assert result.total_weight == 1.0
        assert len(result.hops) == 1
        assert "data_bundle" in result.translated_message

    def test_multi_hop_handoff(self):
        """A2A → MCP → ACP multi-hop chain."""
        orch = self._make_orchestrator()

        def mcp_to_acp(message):
            return {"acp_content": message.get("data_bundle")}

        orch.translator._mappers[("MCP", "ACP")] = mcp_to_acp
        orch.protocol_graph.add_translation_edge("MCP", "ACP", weight=1.5)

        msg = {"payload": {"task": "test"}, "session": "s01"}
        token = self._get_test_token()
        result = orch.handoff(msg, "A2A", "ACP", eat=token)

        assert result.route == ["A2A", "MCP", "ACP"]
        assert result.total_weight == 2.5
        assert "acp_content" in result.translated_message

    def test_handoff_no_route_raises(self):
        orch = self._make_orchestrator()
        orch.protocol_graph.add_protocol("XYZ")
        token = self._get_test_token()

        with pytest.raises(HandoffRoutingError):
            orch.handoff({"data": 1}, "MCP", "XYZ", eat=token)

    def test_handoff_prefers_optimal_route(self):
        orch = self._make_orchestrator()
        orch.translator._mappers[("A2A", "ACP")] = lambda m: {"lossy": True}
        orch.protocol_graph.add_translation_edge("A2A", "ACP", weight=10.0)

        orch.translator._mappers[("MCP", "ACP")] = lambda m: {**m, "via_mcp": True}
        orch.protocol_graph.add_translation_edge("MCP", "ACP", weight=1.0)

        token = self._get_test_token()
        result = orch.handoff({"payload": {"x": 1}}, "A2A", "ACP", eat=token)
        assert result.route == ["A2A", "MCP", "ACP"]
        assert result.translated_message.get("via_mcp") is True

    def test_unauthorized_scope_raises(self):
        """EAT with restricted scope should fail."""
        orch = self._make_orchestrator()
        # Token only allowed for A2A -> MCP
        token = self._get_test_token(tool_permissions={"translator": ["MCP"]})
        
        # This should fail if we try to go to ACP
        with pytest.raises(HandoffAuthorizationError, match="does not authorize handoff"):
            orch.handoff({"p": 1}, "A2A", "ACP", eat=token)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
