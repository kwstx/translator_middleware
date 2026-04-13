from __future__ import annotations
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)

class GlobalData:
    """
    A centralized data store that lives outside the LLM. 
    All collected and validated data is written into and read from this store
    by tool calls, ensuring the model never holds or manipulates raw state directly.
    """
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Stores a value in the global data store."""
        logger.info("global_data_set", key=key, value_type=type(value).__name__)
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a value from the global data store."""
        value = self._store.get(key, default)
        logger.info("global_data_get", key=key, found=key in self._store)
        return value

    def delete(self, key: str) -> bool:
        """Removes a key from the global data store."""
        if key in self._store:
            del self._store[key]
            logger.info("global_data_delete", key=key, success=True)
            return True
        logger.info("global_data_delete", key=key, success=False)
        return False

    def clear(self) -> None:
        """Clears all data from the global data store."""
        self._store.clear()
        logger.info("global_data_cleared")

    def all(self) -> Dict[str, Any]:
        """Returns all data in the global data store."""
        return self._store.copy()

from .types import ToolDefinition, ToolAction

# The global instance used by tools
_global_instance = GlobalData()

def get_global_data() -> GlobalData:
    """Returns the singleton GlobalData instance."""
    return _global_instance

def store_data(key: str, value: Any) -> str:
    """
    Writes data to the GlobalData store. 
    Use this to persist validated information outside the LLM context.
    """
    get_global_data().set(key, value)
    return f"Successfully stored '{key}' in GlobalData."

def retrieve_data(key: str) -> Any:
    """
    Reads data from the GlobalData store.
    Use this to access previously gathered information.
    """
    return get_global_data().get(key)

def delete_data(key: str) -> str:
    """
    Removes data from the GlobalData store.
    """
    success = get_global_data().delete(key)
    if success:
        return f"Successfully deleted '{key}' from GlobalData."
    return f"Key '{key}' not found in GlobalData."

# Tool Definitions for registration
STORE_DATA_TOOL = ToolDefinition(
    name="store_data",
    description="Writes validated data to the GlobalData store. Use this to persist state outside your own context.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The unique identifier for the data piece."},
            "value": {"type": "object", "description": "The value to store. Can be a dict, string, list, or number."}
        },
        "required": ["key", "value"]
    }
)

RETRIEVE_DATA_TOOL = ToolDefinition(
    name="retrieve_data",
    description="Reads data from the GlobalData store by key. Use this to access previously persisted information.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The unique identifier for the data piece."}
        },
        "required": ["key"]
    }
)

DELETE_DATA_TOOL = ToolDefinition(
    name="delete_data",
    description="Removes data from the GlobalData store by key. Use this to maintain a clean state.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The unique identifier for the data piece to remove."}
        },
        "required": ["key"]
    }
)
