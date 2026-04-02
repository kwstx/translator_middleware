from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple
import os

from fastapi import HTTPException
from owlready2 import World
import structlog

from app.core.config import settings
from app.db.models import ToolRegistry

logger = structlog.get_logger(__name__)


_ACTION_ALIASES = {
    "call": "execute",
    "run": "execute",
    "invoke": "execute",
    "get": "read",
    "list": "read",
    "query": "read",
    "search": "read",
    "update": "write",
    "create": "write",
    "delete": "write",
}

_SAFE_ARG_KEYS = {"limit", "page", "offset", "sort", "order", "direction", "fields"}


@dataclass(frozen=True)
class SemanticScope:
    action: str
    concept: str


def _normalize_action(action: str) -> str:
    if not action:
        return ""
    action_norm = action.strip().lower()
    return _ACTION_ALIASES.get(action_norm, action_norm)


def _parse_scope(scope: str) -> Optional[SemanticScope]:
    if not scope or ":" not in scope:
        return None
    action, concept = scope.split(":", 1)
    action = _normalize_action(action)
    concept = concept.strip().lower()
    if not action or not concept:
        return None
    return SemanticScope(action=action, concept=concept)


@lru_cache(maxsize=1)
def _load_security_world() -> World:
    world = World()
    ontology_path = settings.SEMANTIC_SCOPE_ONTOLOGY_PATH
    abs_path = os.path.abspath(ontology_path)
    if not os.path.exists(abs_path):
        logger.warning("Semantic scope ontology file missing", path=abs_path)
        return world
    file_url = f"file://{abs_path.replace(os.sep, '/')}"
    world.get_ontology(file_url).load()
    return world


def _concept_exists(world: World, concept: str) -> bool:
    if not concept:
        return False
    return world.search_one(name=concept.replace("-", "_")) is not None or world.search_one(name=concept) is not None


def _concept_descendants(world: World, concept: str) -> List[str]:
    name_variants = {concept, concept.replace("-", "_")}
    for name in name_variants:
        cls = world.search_one(name=name)
        if cls:
            descendants = {c.name.replace("_", "-").lower() for c in cls.descendants()}
            return sorted(descendants)
    return []


def _concept_equivalents(world: World, concept: str) -> List[str]:
    name_variants = {concept, concept.replace("-", "_")}
    equivalents = set()
    for name in name_variants:
        cls = world.search_one(name=name)
        if cls and hasattr(cls, "equivalent_to"):
            for eq in cls.equivalent_to:
                if hasattr(eq, "name"):
                    equivalents.add(eq.name.replace("_", "-").lower())
    return sorted(equivalents)


class SemanticAuthorizationService:
    def __init__(self):
        self.world = _load_security_world()

    def _allowed_concepts_for_action(self, token_scopes: Iterable[str], action: str) -> List[str]:
        action_norm = _normalize_action(action)
        allowed: List[str] = []
        for scope in token_scopes:
            parsed = _parse_scope(scope)
            if not parsed:
                continue
            if parsed.action not in {action_norm, "*", "all"}:
                # Allow execute scopes to cover generic tool invocation
                if not (parsed.action == "execute" and action_norm == "execute"):
                    continue
            allowed.append(parsed.concept)
        expanded: set[str] = set()
        for concept in allowed:
            expanded.add(concept)
            expanded.update(_concept_descendants(self.world, concept))
            expanded.update(_concept_equivalents(self.world, concept))
        return sorted(expanded)

    def _required_scopes_for_tool(self, tool: ToolRegistry, action: str) -> List[SemanticScope]:
        required_scopes: List[SemanticScope] = []
        for scope in tool.required_permissions or []:
            parsed = _parse_scope(scope)
            if parsed:
                required_scopes.append(parsed)
        if tool.execution_metadata and tool.execution_metadata.metadata:
            for scope in tool.execution_metadata.metadata.get("semantic_requirements", []) or []:
                parsed = _parse_scope(scope)
                if parsed:
                    required_scopes.append(parsed)
        # If nothing is specified, default to requiring execute:tool-invocation for tool calls
        if not required_scopes:
            required_scopes.append(SemanticScope(action="execute", concept="tool-invocation"))
        action_norm = _normalize_action(action)
        return [scope for scope in required_scopes if scope.action in {action_norm, "*", "all", "execute"}]

    def _infer_concept_for_arg(self, key: str) -> Optional[str]:
        if not key:
            return None
        key_norm = key.strip().lower().replace("_", "-")
        if _concept_exists(self.world, key_norm):
            return key_norm
        return None

    def _filter_args(
        self,
        args: Dict[str, Any],
        allowed_concepts: List[str],
        action: str,
        parameter_map: Dict[str, str],
    ) -> Tuple[Dict[str, Any], List[str]]:
        if not args:
            return args, []
        allowed_set = {c.lower() for c in allowed_concepts}
        filtered: Dict[str, Any] = {}
        denied: List[str] = []
        for key, value in args.items():
            if key in _SAFE_ARG_KEYS:
                filtered[key] = value
                continue
            mapped = parameter_map.get(key)
            if mapped:
                concept = mapped.strip().lower()
            else:
                concept = self._infer_concept_for_arg(key)
            if concept and allowed_set and concept not in allowed_set:
                denied.append(key)
                continue
            filtered[key] = value
        return filtered, denied

    def enforce(
        self,
        token_payload: Dict[str, Any],
        tool: ToolRegistry,
        action: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        action_norm = _normalize_action(action or "")
        token_scopes = token_payload.get("semantic_scopes") or []
        if not isinstance(token_scopes, list):
            token_scopes = []

        required_scopes = self._required_scopes_for_tool(tool, action_norm)
        allowed_concepts = self._allowed_concepts_for_action(token_scopes, action_norm)

        # Enforce required scopes using ontology-based matching
        if required_scopes:
            matched = False
            for scope in required_scopes:
                if scope.concept in allowed_concepts:
                    matched = True
                    break
                if scope.concept.replace("_", "-").lower() in allowed_concepts:
                    matched = True
                    break
            if not matched:
                if settings.SEMANTIC_AUTH_FAIL_CLOSED:
                    raise HTTPException(status_code=403, detail="Semantic scope does not authorize this action.")
                logger.warning("Semantic scope mismatch (fail-open)", action=action_norm, tool=tool.name)

        parameter_map = {}
        if tool.execution_metadata and tool.execution_metadata.metadata:
            parameter_map = tool.execution_metadata.metadata.get("semantic_parameter_map", {}) or {}

        if "tool-invocation" in {c.lower() for c in allowed_concepts}:
            return args or {}

        filtered_args, denied = self._filter_args(args or {}, allowed_concepts, action_norm, parameter_map)
        if denied:
            if action_norm in {"read", "list", "query"}:
                logger.info("Semantic scope narrowing applied", denied=denied, tool=tool.name, action=action_norm)
                return filtered_args
            raise HTTPException(status_code=403, detail=f"Semantic scope does not permit parameters: {', '.join(denied)}")
        return filtered_args
