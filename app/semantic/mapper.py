from owlready2 import get_ontology, World, Thing
from typing import Any, Dict, Optional, List
import os
import structlog
import jsonschema
from pyDatalog import pyDatalog
from app.core.config import settings
from app.core.redis_client import get_redis_client
from sqlalchemy.ext.asyncio import AsyncSession
pyDatalog.create_terms('X, Y, map_field')

logger = structlog.get_logger(__name__)

class SemanticMapper:
    def __init__(self, ontology_path: str = None, session: Optional[AsyncSession] = None):
        """
        Initialize the SemanticMapper.
        :param ontology_path: Absolute or relative path to the OWL file.
        :param session: Database session for rule retrieval.
        """
        self.world = World()
        self.ontology_path = ontology_path
        self.ontology = None
        self.session = session
        self.redis = get_redis_client()
        self.cache_ttl_seconds = settings.SEMANTIC_CACHE_TTL_SECONDS
        
        # Lazy loading: we don't load immediately unless requested
        # if ontology_path:
        #     self.load_ontology(ontology_path)

    def load_ontology(self, path: str):
        """
        Loads an OWL ontology file using Owlready2.
        """
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            logger.error(f"Ontology file not found at {abs_path}")
            raise FileNotFoundError(f"Ontology file not found at {abs_path}")
        
        try:
            # Owlready2 expects 'file://' prefix for local files
            # On Windows, abspath returns backslashes which must be converted for file:// URLs
            file_url = f"file://{abs_path.replace(os.sep, '/')}"
            self.ontology = self.world.get_ontology(file_url).load()
            logger.info(f"Successfully loaded ontology from {abs_path}")
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            raise

    def resolve_equivalent(self, concept: str, source_protocol: str) -> str:
        """
        Searches the ontology for synonyms or equivalents in target protocols.
        """
        if not self.ontology and self.ontology_path:
            self.load_ontology(self.ontology_path)
            
        if not self.ontology:
            return f"Error: Ontology not loaded."

        cache_key = f"semantic:equivalent:{source_protocol}:{concept}"
        cached_value = self._cache_get(cache_key)
        if cached_value:
            return cached_value

        namespaces = {
            "A2A": "http://agent.middleware.org/A2A#",
            "MCP": "http://agent.middleware.org/MCP#",
            "ACP": "http://agent.middleware.org/ACP#",
            "CLI": "http://agent.middleware.org/CLI#",
            "HTTP": "http://agent.middleware.org/HTTP#",
            "BASE": "http://agent.middleware.org/protocols.owl#",
        }

        if source_protocol not in namespaces:
            return f"Error: Unknown protocol '{source_protocol}'"

        target_iri = f"{namespaces[source_protocol]}{concept}"
        source_concept = self.world.search_one(iri=target_iri)
        
        if not source_concept:
            source_concept = self.world.search_one(name=concept)
            if not source_concept:
                result = f"Concept '{concept}' not found."
                self._cache_set(cache_key, result)
                return result

        equivalents = []
        if hasattr(source_concept, "equivalent_to"):
            for eq in source_concept.equivalent_to:
                if isinstance(eq, type):
                    equivalents.append(eq)
        
        for cls in self.world.classes():
            if source_concept in cls.equivalent_to:
                if cls not in equivalents:
                    equivalents.append(cls)

        if not equivalents:
            result = f"No equivalents found for {source_protocol}:{concept}"
            self._cache_set(cache_key, result)
            return result

        for eq in equivalents:
            eq_iri = str(eq.iri)
            for proto, ns in namespaces.items():
                if eq_iri.startswith(ns) and proto != source_protocol and proto != "BASE":
                    concept_name = eq_iri.replace(ns, "")
                    result = f"{proto}:{concept_name}"
                    self._cache_set(cache_key, result)
                    return result

        result = f"Equivalents found but none in target protocols: {[str(e.iri) for e in equivalents]}"
        self._cache_set(cache_key, result)
        return result

    def resolve_to_ontology_concept(self, concept: str, source_protocol: str) -> str:
        """
        Maps a protocol-specific concept to a canonical ontology concept name.
        Falls back to the original concept when no ontology match is found.
        """
        if not self.ontology and self.ontology_path:
            self.load_ontology(self.ontology_path)
            
        if not self.ontology:
            return concept

        source_protocol = source_protocol.upper()
        namespaces = {
            "A2A": "http://agent.middleware.org/A2A#",
            "MCP": "http://agent.middleware.org/MCP#",
            "ACP": "http://agent.middleware.org/ACP#",
            "CLI": "http://agent.middleware.org/CLI#",
            "HTTP": "http://agent.middleware.org/HTTP#",
            "BASE": "http://agent.middleware.org/protocols.owl#",
        }

        namespace = namespaces.get(source_protocol)
        source_concept = None
        if namespace:
            source_concept = self.world.search_one(iri=f"{namespace}{concept}")

        if not source_concept:
            source_concept = self.world.search_one(name=concept)

        if not source_concept:
            return concept

        if hasattr(source_concept, "equivalent_to"):
            for eq in source_concept.equivalent_to:
                if isinstance(eq, type):
                    return getattr(eq, "name", concept) or concept

        return getattr(source_concept, "name", concept) or concept

    def resolve_from_ontology_concept(self, concept: str, target_protocol: str) -> str:
        """
        Maps a canonical ontology concept name into a target protocol's concept name.
        Returns the original concept if no match is found.
        """
        if not self.ontology and self.ontology_path:
            self.load_ontology(self.ontology_path)
            
        if not self.ontology:
            return concept

        target_protocol = target_protocol.upper()
        namespaces = {
            "A2A": "http://agent.middleware.org/A2A#",
            "MCP": "http://agent.middleware.org/MCP#",
            "ACP": "http://agent.middleware.org/ACP#",
            "CLI": "http://agent.middleware.org/CLI#",
            "HTTP": "http://agent.middleware.org/HTTP#",
            "BASE": "http://agent.middleware.org/protocols.owl#",
        }

        target_namespace = namespaces.get(target_protocol)
        source_concept = self.world.search_one(name=concept)
        if not source_concept:
            # Try protocol-specific IRI as a fallback
            if target_namespace:
                source_concept = self.world.search_one(iri=f"{target_namespace}{concept}")
            if not source_concept:
                return concept

        if hasattr(source_concept, "equivalent_to"):
            for eq in source_concept.equivalent_to:
                eq_iri = str(eq.iri)
                if target_namespace and eq_iri.startswith(target_namespace):
                    return eq_iri.replace(target_namespace, "")

        return concept

    def DataSiloResolver(
        self, 
        source_data: dict, 
        source_schema: dict, 
        target_schema: dict, 
        source_protocol: str, 
        target_protocol: str,
        custom_rules: Optional[Dict[str, str]] = None
    ) -> dict:
        """
        Resolves data silos by detecting schema differences, flattening nested objects,
        and renaming fields based on ontology mappings and PyDatalog rules.
        """
        logger.info(f"Resolving data silo from {source_protocol} to {target_protocol}")

        # 1. JSON Schema Validation
        try:
            jsonschema.validate(instance=source_data, schema=source_schema)
            logger.info("Source data validated successfully.")
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Schema validation failed: {e.message}")
            raise ValueError(f"Invalid source data: {e.message}")

        # 2. Flatten Nested Objects
        flattened_data = self._flatten_dict(source_data)
        logger.debug(f"Flattened data: {flattened_data}")

        # 3. Dynamic Mapping via PyDatalog Rules
        pyDatalog.clear()
        
        # Load rules from DB if mapping exists
        db_rules = {}
        # In a real implementation we would make this properly async or fetch rules beforehand
        # For now we'll assume they're passed, but we added the session hook for future extensions.
        if custom_rules:
            db_rules.update(custom_rules)
            
        for src_field, tgt_field in db_rules.items():
            + map_field(src_field, tgt_field)
        
        if db_rules:
            logger.info("Semantic mapping rules loaded", rule_count=len(db_rules))

        # 4. Resolve field names using Ontology Mappings
        mapped_data = {}
        for flat_key, value in flattened_data.items():
            # Check PyDatalog rules first
            res = map_field(flat_key, Y)
            if res:
                target_key = str(res[0][0])
                logger.info(f"PyDatalog mapping: {flat_key} -> {target_key}")
            else:
                # Fallback to SemanticMapper.resolve_equivalent if it's a single concept
                leaf_key = flat_key.split('.')[-1]
                semantic_res = self.resolve_equivalent(leaf_key, source_protocol)
                
                if target_protocol.upper() in semantic_res.upper():
                    target_key = semantic_res.split(':')[-1]
                    logger.info(f"Ontology mapping: {flat_key} -> {target_key}")
                else:
                    target_key = flat_key # Default to same name
            
            mapped_data[target_key] = value

        # 5. Reconstruct structure based on target_schema (simple version)
        return mapped_data

    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str = '.') -> dict:
        """
        Recursively flattens a nested dictionary.
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _cache_get(self, key: str) -> str | None:
        if not self.redis:
            return None
        try:
            return self.redis.get(key)
        except Exception as exc:
            logger.warning("Redis cache get failed", key=key, error=str(exc))
            return None

    def _cache_set(self, key: str, value: str) -> None:
        if not self.redis:
            return
        try:
            self.redis.setex(key, self.cache_ttl_seconds, value)
        except Exception as exc:
            logger.warning("Redis cache set failed", key=key, error=str(exc))

if __name__ == "__main__":
    # Quick test
    from app.core.logging import configure_logging
    configure_logging()
    try:
        mapper = SemanticMapper("app/semantic/protocols.owl")
        result = mapper.resolve_equivalent("task_handoff", "A2A")
        print(f"Mapping A2A:task_handoff -> {result}")
    except Exception as e:
        print(f"Test failed: {e}")
