from typing import Dict, Any, Callable
from datetime import datetime, date
import logging
from app.core.exceptions import ProtocolMismatchError, TranslationError

logger = logging.getLogger(__name__)

class TranslatorEngine:
    """
    Core engine for dynamic protocol translation.
    Handles structural transformations between different agent protocols.
    """

    def __init__(self):
        # Dictionary mapping (source_protocol, target_protocol) to the transformation function
        self._mappers: Dict[tuple[str, str], Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            ("A2A", "MCP"): self._translate_a2a_to_mcp,
            # Placeholder for other mappings
            # ("MCP", "A2A"): self._translate_mcp_to_a2a,
        }

    @property
    def supported_pairs(self) -> list[tuple[str, str]]:
        """Returns all registered (source_protocol, target_protocol) pairs."""
        return list(self._mappers.keys())

    def translate(self, source_message: Dict[str, Any], source_protocol: str, target_protocol: str) -> Dict[str, Any]:
        """
        Translates a message from one protocol to another.
        
        :param source_message: The original message dictionary
        :param source_protocol: The protocol string of the source (e.g., 'A2A')
        :param target_protocol: The protocol string of the target (e.g., 'MCP')
        :return: The translated message dictionary
        :raises ProtocolMismatchError: If no translation rule exists for the protocol pair
        :raises TranslationError: If an error occurs during the translation process
        """
        src = source_protocol.upper()
        tgt = target_protocol.upper()
        mapping_key = (src, tgt)

        logger.info(f"Translating message from {src} to {tgt}")

        if mapping_key not in self._mappers:
            logger.error(f"No translation rule found for {src} -> {tgt}")
            raise ProtocolMismatchError(f"No translation rule found for {src} -> {tgt}")

        try:
            return self._mappers[mapping_key](source_message)
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise TranslationError(f"Failed to translate message: {str(e)}")

    def _translate_a2a_to_mcp(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specific mapping rules for A2A to MCP:
        - Transform 'payload' key to 'data_bundle'
        - Serialize all date/datetime objects to ISO 8601 format
        """
        translated = {}
        
        for key, value in message.items():
            # Apply key mapping
            new_key = "data_bundle" if key == "payload" else key
            
            # Apply value transformations (specifically date serialization)
            new_value = self._process_value(value)
            
            translated[new_key] = new_value
            
        return translated

    def _process_value(self, value: Any) -> Any:
        """
        Recursively processes values to handle date serialization and nested structures.
        """
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        
        elif isinstance(value, dict):
            return {k: self._process_value(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._process_value(item) for item in value]
        
        return value

if __name__ == "__main__":
    # Basic verification
    logging.basicConfig(level=logging.INFO)
    engine = TranslatorEngine()
    
    test_message = {
        "id": "msg_001",
        "timestamp": datetime.now(),
        "payload": {
            "action": "thermal_check",
            "due_date": datetime(2026, 3, 15, 12, 0)
        },
        "metadata": ["critical", "high-priority"]
    }
    
    try:
        result = engine.translate(test_message, "A2A", "MCP")
        print("Translation successful:")
        import json
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Translation failed: {e}")
