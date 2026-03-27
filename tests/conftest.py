from unittest.mock import MagicMock
import sys
import pytest

# 1. Mock pyswip before any app code is imported
mock_pyswip = MagicMock()
sys.modules["pyswip"] = mock_pyswip

# 2. Mock owlready2 if needed
mock_owl = MagicMock()
sys.modules["owlready2"] = mock_owl

# 3. Mock pyDatalog
mock_datalog = MagicMock()
mock_datalog_pkg = MagicMock()
mock_datalog_pkg.pyDatalog = mock_datalog
sys.modules["pyDatalog"] = mock_datalog_pkg

@pytest.fixture(autouse=True)
def mock_external_deps():
    # This fixture ensures mocks are in place for all tests
    pass
