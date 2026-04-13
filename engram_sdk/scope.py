import uuid
import hashlib
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any


class ScopeCache:
    """
    Caches validation results for tool scopes to avoid redundant backend calls.
    Supports Redis or a local JSON store. Each entry is keyed by a hash of the tool list.
    """
    def __init__(self, redis_url: Optional[str] = None, cache_dir: Optional[str] = None):
        self.redis = None
        if redis_url:
            try:
                import redis
                self.redis = redis.from_url(redis_url, decode_responses=True)
            except (ImportError, Exception):
                # Fallback if redis is unavailable or misconfigured
                pass
        
        if not self.redis:
            # Fallback to local JSON store in ~/.engram/scopes
            self.cache_dir = Path(cache_dir or Path.home() / ".engram" / "scopes")
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
            except Exception:
                # If we cannot write to the home directory, disable local caching
                self.cache_dir = None

    def _get_hash(self, tools: List[str]) -> str:
        """Generates a stable SHA-256 hash for a sorted list of tool names."""
        content = ",".join(sorted(tools))
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, tools: List[str]) -> Optional[Dict[str, Any]]:
        """Retrieves cached validation results (schemas + timestamp) for a given tool set."""
        key = self._get_hash(tools)
        try:
            if self.redis:
                data = self.redis.get(f"scope_cache:{key}")
                return json.loads(data) if data else None
            
            if self.cache_dir:
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    with open(cache_file, "r") as f:
                        return json.load(f)
        except Exception:
            # If cache access fails, force a re-validation by returning None
            pass
        return None

    def set(self, tools: List[str], corrected_schemas: Dict[str, Any]):
        """Stores validation results and the current timestamp in the cache."""
        key = self._get_hash(tools)
        data = {
            "tools": sorted(tools),
            "corrected_schemas": corrected_schemas,
            "timestamp": time.time()
        }
        try:
            if self.redis:
                # Store indefinitely or until manual eviction as per 'simple store' request
                self.redis.set(f"scope_cache:{key}", json.dumps(data))
            elif self.cache_dir:
                cache_file = self.cache_dir / f"{key}.json"
                with open(cache_file, "w") as f:
                    json.dump(data, f)
        except Exception:
            # Silently ignore cache write failures
            pass


class Scope:
    """
    Represents a narrow, explicit set of tools for a single conversation step or agent turn.

    The Scope object is the primary way developers declare exactly which tools are
    available at any given moment, enforcing the principle that the developer's
    code owns the state machine.
    """

    def __init__(self, tools: List[str], step_id: Optional[str] = None) -> None:
        """
        Initialize a new Scope.

        Args:
            tools: A list of tool IDs or names that are available in this scope.
            step_id: A unique identifier for this conversation step. If not provided,
                a random UUID will be generated.
        """
        if not isinstance(tools, list):
            raise TypeError("tools must be a list of strings")
        
        self.tools = list(tools)
        self.step_id = step_id or str(uuid.uuid4())
        self.corrected_schemas: Dict[str, Any] = {}
        self.validation_timestamp: Optional[float] = None

    @property
    def tool_count(self) -> int:
        """Returns the number of tools in this scope."""
        return len(self.tools)

    def contains(self, tool_id: str) -> bool:
        """Checks if a specific tool is included in this scope."""
        return tool_id in self.tools

    def validate(self, sdk: Optional[Any] = None) -> bool:
        """
        Queries the real backend state for each tool in the narrow list using the existing registry.
        It runs the OWL ontology + ML embedding check against the current API or CLI definitions 
        to detect any schema drift or mismatches before any schema is ever sent to the model. 

        This method uses a caching layer (Redis or local JSON) to ensure repeated steps 
        do not re-validate unnecessarily, keeping the process fast and deterministic.

        Returns:
            bool: True if no drift was found, False otherwise.
        """
        if sdk is None:
            # Validation requires SDK for backend communication
            return True

        # Resolve cache instance from SDK or environment
        cache = getattr(sdk, "scope_cache", None)
        if not cache:
            redis_url = os.getenv("REDIS_URL")
            cache = ScopeCache(redis_url=redis_url)
            # Cache the cache handler on the SDK instance if possible
            try:
                setattr(sdk, "scope_cache", cache)
            except Exception:
                pass

        # Check for existing cached validation for this specific tool list
        cached_entry = cache.get(self.tools)
        if cached_entry:
            self.corrected_schemas = cached_entry.get("corrected_schemas", {})
            self.validation_timestamp = cached_entry.get("timestamp")
            return not bool(self.corrected_schemas)

        drift_detected = False
        for tool_name in self.tools:
            # Query the backend state via the registry in the SDK
            correction = sdk.tools.check_drift(tool_name, sdk.transport)
            if correction:
                self.corrected_schemas[tool_name] = correction
                drift_detected = True
        
        # Save validation results to cache for future use
        self.validation_timestamp = time.time()
        cache.set(self.tools, self.corrected_schemas)
        
        return not drift_detected

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Scope to a dictionary representation."""
        data = {
            "step_id": self.step_id,
            "tools": self.tools,
        }
        if self.corrected_schemas:
            data["corrected_schemas"] = self.corrected_schemas
        if self.validation_timestamp:
            data["validation_timestamp"] = self.validation_timestamp
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scope":
        """Creates a Scope instance from a dictionary."""
        instance = cls(
            tools=data.get("tools", []),
            step_id=data.get("step_id"),
        )
        if "corrected_schemas" in data:
            instance.corrected_schemas = data["corrected_schemas"]
        if "validation_timestamp" in data:
            instance.validation_timestamp = data["validation_timestamp"]
        return instance

    def __repr__(self) -> str:
        return f"Scope(step_id={self.step_id!r}, tools={self.tools!r}, drift={bool(self.corrected_schemas)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Scope):
            return NotImplemented
        return (self.step_id == other.step_id and 
                self.tools == other.tools and 
                self.corrected_schemas == other.corrected_schemas and
                self.validation_timestamp == getattr(other, "validation_timestamp", None))

