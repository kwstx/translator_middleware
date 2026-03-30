from typing import Dict, Any, Callable, Optional, Tuple, List
from datetime import datetime, date, timezone
import copy
import structlog
from app.core.exceptions import ProtocolMismatchError, TranslationError
from app.core.metrics import record_translation_error, record_translation_success
from app.messaging.intent_resolver import IntentResolver

logger = structlog.get_logger(__name__)

class TranslatorEngine:
    """
    Core engine for dynamic protocol translation.
    Handles structural transformations between different agent protocols.
    """

    def __init__(
        self,
        expected_versions: Optional[Dict[str, str]] = None,
        delta_mappings: Optional[Dict[str, Dict[Tuple[str, str], Dict[str, Any]]]] = None,
    ):
        # Dictionary mapping (source_protocol, target_protocol) to the transformation function
        self._mappers: Dict[tuple[str, str], Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            ("A2A", "MCP"): self._translate_a2a_to_mcp,
            ("NL", "MCP"): self._translate_nl_to_mcp,
            # Placeholder for other mappings
            # ("MCP", "A2A"): self._translate_mcp_to_a2a,
        }
        self._expected_versions: Dict[str, str] = {
            k.upper(): self._normalize_version(v)
            for k, v in (expected_versions or {"A2A": "2"}).items()
        }
        self._delta_mappings: Dict[str, Dict[Tuple[str, str], Dict[str, Any]]] = (
            delta_mappings or {}
        )
        self.intent_resolver = IntentResolver()

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

        logger.info("Translating message", source_protocol=src, target_protocol=tgt)

        if mapping_key not in self._mappers:
            logger.error(
                "No translation rule found",
                source_protocol=src,
                target_protocol=tgt,
            )
            record_translation_error("engine", src, tgt)
            raise ProtocolMismatchError(f"No translation rule found for {src} -> {tgt}")

        try:
            normalized_message = self._apply_version_deltas_if_needed(source_message, src)
            result = self._mappers[mapping_key](normalized_message)
            record_translation_success("engine", src, tgt)
            return result
        except Exception as e:
            logger.error(
                "Translation failed",
                source_protocol=src,
                target_protocol=tgt,
                error=str(e),
            )
            record_translation_error("engine", src, tgt)
            raise TranslationError(f"Failed to translate message: {str(e)}")

    async def refresh_delta_mappings(self, session) -> None:
        """
        Refreshes protocol version delta mappings from the database.
        """
        from sqlmodel import select
        from app.db.models import ProtocolVersionDelta

        result = await session.execute(select(ProtocolVersionDelta))
        rows = result.scalars().all()

        delta_map: Dict[str, Dict[Tuple[str, str], Dict[str, Any]]] = {}
        for row in rows:
            protocol = row.protocol.upper()
            from_v = self._normalize_version(row.from_version)
            to_v = self._normalize_version(row.to_version)
            delta_map.setdefault(protocol, {})[(from_v, to_v)] = row.delta_rules or {}

        self._delta_mappings = delta_map
        logger.info(
            "Delta mappings refreshed",
            protocols=list(self._delta_mappings.keys()),
            mapping_count=sum(len(v) for v in self._delta_mappings.values()),
        )

    def register_delta_mapping(
        self, protocol: str, from_version: str, to_version: str, delta_rules: Dict[str, Any]
    ) -> None:
        protocol_key = protocol.upper()
        from_v = self._normalize_version(from_version)
        to_v = self._normalize_version(to_version)
        self._delta_mappings.setdefault(protocol_key, {})[(from_v, to_v)] = delta_rules

    def _apply_version_deltas_if_needed(
        self, message: Dict[str, Any], source_protocol: str
    ) -> Dict[str, Any]:
        expected_version = self._expected_versions.get(source_protocol)
        if not expected_version:
            return message

        source_version, version_path = self._extract_version(message)
        if source_version is None:
            logger.warning(
                "No source version found; skipping version normalization",
                source_protocol=source_protocol,
                expected_version=expected_version,
            )
            return message

        if source_version == expected_version:
            return message

        logger.info(
            "Version mismatch detected",
            source_protocol=source_protocol,
            source_version=source_version,
            expected_version=expected_version,
        )

        if source_protocol not in self._delta_mappings:
            raise TranslationError(
                f"No delta mappings loaded for protocol {source_protocol}"
            )

        path = self._find_version_path(
            source_protocol, source_version, expected_version
        )
        if not path:
            raise TranslationError(
                f"No delta mapping path for {source_protocol} "
                f"{source_version} -> {expected_version}"
            )

        upgraded = copy.deepcopy(message)
        for from_v, to_v, rules in path:
            upgraded = self._apply_delta_rules(upgraded, rules)
            self._set_version(upgraded, version_path, to_v)
            logger.info(
                "Applied version delta",
                source_protocol=source_protocol,
                from_version=from_v,
                to_version=to_v,
            )

        return upgraded

    def _find_version_path(
        self, protocol: str, source_version: str, expected_version: str
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        edges = self._delta_mappings.get(protocol, {})
        adjacency: Dict[str, List[str]] = {}
        for (from_v, to_v) in edges.keys():
            adjacency.setdefault(from_v, []).append(to_v)

        queue: List[str] = [source_version]
        parents: Dict[str, Optional[str]] = {source_version: None}

        while queue:
            current = queue.pop(0)
            if current == expected_version:
                break
            for neighbor in adjacency.get(current, []):
                if neighbor not in parents:
                    parents[neighbor] = current
                    queue.append(neighbor)

        if expected_version not in parents:
            return []

        # Reconstruct path
        path_versions: List[str] = []
        current = expected_version
        while current is not None:
            path_versions.append(current)
            current = parents[current]
        path_versions.reverse()

        path_edges: List[Tuple[str, str, Dict[str, Any]]] = []
        for i in range(len(path_versions) - 1):
            from_v = path_versions[i]
            to_v = path_versions[i + 1]
            rules = edges.get((from_v, to_v), {})
            path_edges.append((from_v, to_v, rules))

        return path_edges

    def _apply_delta_rules(self, message: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        if not rules:
            return message

        renames = rules.get("rename", {})
        for old_path, new_path in renames.items():
            found, value = self._get_by_path(message, old_path)
            if not found:
                continue
            self._set_by_path(message, new_path, value)
            self._delete_by_path(message, old_path)

        drops = rules.get("drop", [])
        for drop_path in drops:
            self._delete_by_path(message, drop_path)

        sets = rules.get("set", {})
        for set_path, set_value in sets.items():
            self._set_by_path(message, set_path, set_value)

        return message

    def _extract_version(self, message: Dict[str, Any]) -> Tuple[Optional[str], Optional[Tuple[str, ...]]]:
        version_paths = [
            ("protocol_version",),
            ("version",),
            ("schema_version",),
            ("metadata", "version"),
            ("meta", "version"),
        ]
        for path in version_paths:
            found, value = self._get_by_path(message, ".".join(path))
            if found:
                if value is None:
                    return None, path
                return self._normalize_version(value), path
        return None, None

    def _set_version(
        self, message: Dict[str, Any], path: Optional[Tuple[str, ...]], version: str
    ) -> None:
        target_path = ".".join(path) if path else "protocol_version"
        self._set_by_path(message, target_path, version)

    def _normalize_version(self, version: Any) -> str:
        text = str(version).strip().lower()
        if text.startswith("v"):
            text = text[1:]
        return text

    def _get_by_path(self, message: Dict[str, Any], path: str) -> Tuple[bool, Any]:
        parts = [p for p in path.split(".") if p]
        current: Any = message
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]
        return True, current

    def _set_by_path(self, message: Dict[str, Any], path: str, value: Any) -> None:
        parts = [p for p in path.split(".") if p]
        if not parts:
            return
        current: Any = message
        for part in parts[:-1]:
            if not isinstance(current, dict):
                return
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        if isinstance(current, dict):
            current[parts[-1]] = value

    def _delete_by_path(self, message: Dict[str, Any], path: str) -> None:
        parts = [p for p in path.split(".") if p]
        if not parts:
            return
        current: Any = message
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return
            current = current[part]
        if isinstance(current, dict):
            current.pop(parts[-1], None)

    def _translate_a2a_to_mcp(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specific mapping rules for A2A to MCP:
        - Transform 'payload' key to 'data_bundle'
        - Transform 'data.task' to top-level 'coord'
        - Drop 'protocol' field if present
        - Serialize all date/datetime objects to ISO 8601 format
        """
        translated = {}
        
        for key, value in message.items():
            if key == "protocol":
                continue

            if key == "payload":
                translated["data_bundle"] = self._process_value(value)
                continue

            if key == "data":
                if isinstance(value, dict) and "task" in value:
                    translated["coord"] = self._process_value(value["task"])
                else:
                    translated["coord"] = self._process_value(value)
                continue

            # Default passthrough with value normalization
            translated[key] = self._process_value(value)
            
        return translated

    def _translate_nl_to_mcp(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translates a Natural Language (NL) command into structured MCP.
        Uses the IntentResolver for sophisticated prompt decomposition.
        """
        cmd = message.get("command")
        if not cmd and "intent" in message:
             # Already cleaned by Orchestrator
             return message
             
        # Resolve intent synchronously
        resolution = self.intent_resolver.resolve_sync(cmd or "")
        
        if not resolution.tasks:
             return {"intent": "general_query", "content": cmd, "coord": "research"}
             
        # Map primary task to MCP structure
        primary = resolution.tasks[0]
        translated = {
             "intent": primary.intent,
             "capability_tag": primary.capability_tag,
             "coord": "research", # Default MCP coord
             **primary.parameters
        }
        
        # Preserve metadata
        if "metadata" in message:
             translated["metadata"] = self._process_value(message["metadata"])
             
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
    from app.core.logging import configure_logging
    configure_logging()
    engine = TranslatorEngine()
    
    test_message = {
        "id": "msg_001",
        "timestamp": datetime.now(timezone.utc),
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
