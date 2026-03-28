import sys
from unittest.mock import MagicMock

# Manually mock external dependencies
sys.modules["pyswip"] = MagicMock()
sys.modules["owlready2"] = MagicMock()
mock_datalog_pkg = MagicMock()
sys.modules["pyDatalog"] = mock_datalog_pkg

try:
    from reliability.middleware import ReliabilityMiddleware
    print("Success: ReliabilityMiddleware imported!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Failure: {str(e)}")
