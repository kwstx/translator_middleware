from unittest.mock import MagicMock
import sys
sys.modules["pyswip"] = MagicMock()
sys.modules["owlready2"] = MagicMock()
mock_datalog = MagicMock()
mock_datalog_pkg = MagicMock()
mock_datalog_pkg.pyDatalog = mock_datalog
sys.modules["pyDatalog"] = mock_datalog_pkg

print("Checking imports...")
try:
    from app.main import app
    print("app imported")
    from app.api.v1.orchestration import router
    print("orchestration router imported")
    from app.messaging.multi_agent_orchestrator import MultiAgentOrchestrator
    print("multi_agent_orchestrator imported")
    print("All good!")
except Exception as e:
    import traceback
    traceback.print_exc()
