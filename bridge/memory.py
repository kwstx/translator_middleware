from pyswip import Prolog
from owlready2 import get_ontology, World
from pyDatalog import pyDatalog
import os
import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json
from app.semantic.mapper import SemanticMapper
from app.core.config import settings

import sys
try:
    from unittest.mock import MagicMock
except ImportError:
    MagicMock = None

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Memory"])

# ~/.engram/memory.db (Persistence for Prolog facts)
DB_PATH = os.path.expanduser("~/.engram/memory.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

class MemoryWriteRequest(BaseModel):
    agent_id: str
    protocol: str
    payload: Dict[str, Any]

class MemoryQueryResponse(BaseModel):
    key: str
    value: Any
    agent_id: str
    timestamp: float

try:
    pyDatalog.create_terms('A, X, Y, Z, A2, Y2, Z2, latest_fact, fact_data')
except Exception:
    # Handle mock environment
    A = X = Y = Z = A2 = Y2 = Z2 = latest_fact = fact_data = MagicMock() if "unittest.mock" in sys.modules else None

class SwarmMemory:
    def __init__(self):
        self.prolog = Prolog()
        
        # Load existing ontology
        ontology_folder = os.path.join(os.getcwd(), "app/semantic")
        ontology_file = os.path.join(ontology_folder, "protocols.owl")
        self.mapper = SemanticMapper(ontology_file)
        
        # Load existing facts if db exists
        if os.path.exists(DB_PATH):
            self.load_memory()
        
        try:
            # Define conflict resolution rules in pyDatalog
            (latest_fact(X, Y, A, Z) <= 
                fact_data(A, X, Y, Z) & 
                ~ (fact_data(A2, X, Y2, Z2) & (Z2 > Z)))
        except Exception:
            logger.warning("pyDatalog resolution rules not loaded (likely mock environment)")

    def load_memory(self):
        """Loads facts from the persistent store into the Prolog engine."""
        try:
            # We treat memory.db as a Prolog file
            # SWI-Prolog consults the file to load predicates
            self.prolog.consult(DB_PATH)
            logger.info(f"Memory loaded successfully from {DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to load memory from {DB_PATH}: {e}")

    def save_memory(self):
        """Saves current 'fact' predicates from Prolog to the persistent store."""
        try:
            # Query all facts: fact(Agent, Predicate, Value, Timestamp)
            facts = list(self.prolog.query("fact(A, P, V, T)"))
            with open(DB_PATH, 'w', encoding='utf-8') as f:
                for fact in facts:
                    # Escape single quotes in values for Prolog
                    agent = str(fact['A']).replace("'", "\\'")
                    pred = str(fact['P']).replace("'", "\\'")
                    val = fact['V']
                    if isinstance(val, str):
                        escaped = val.replace("'", "\\'")
                        val = f"'{escaped}'"
                    elif isinstance(val, (int, float)):
                        pass
                    else:
                        escaped = str(val).replace("'", "\\'")
                        val = f"'{escaped}'"
                    
                    f.write(f"fact('{agent}', '{pred}', {val}, {fact['T']}).\n")
            logger.info(f"Memory saved to {DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def write(self, agent_id: str, protocol: str, payload: Dict[str, Any]):
        """Reconciles payload fields using the semantic mapper and stores them as versioned facts."""
        timestamp = datetime.now(timezone.utc).timestamp()
        
        # 1. Flatten the payload
        flattened = self.mapper._flatten_dict(payload)
        facts_added = 0
        
        for key, value in flattened.items():
            # 2. Resolve field name to ontology concept
            # We take the leaf key as the potential concept
            leaf_key = key.split('.')[-1]
            resolved = self.mapper.resolve_equivalent(leaf_key, protocol)
            
            # Extract concept from "PROTO:CONCEPT" or use leaf_key if not found
            concept = resolved.split(':')[-1] if ':' in resolved else leaf_key
            
            # 3. Assert to Prolog
            # Use fact(AgentID, Predicate, Value, Timestamp)
            agent_safe = agent_id.replace("'", "\\'")
            concept_safe = concept.replace("'", "\\'")
            
            if isinstance(value, str):
                escaped = value.replace("'", "\\'")
                val_safe = f"'{escaped}'"
            else:
                val_safe = value
                
            self.prolog.assertz(f"fact('{agent_safe}', '{concept_safe}', {val_safe}, {timestamp})")
            facts_added += 1
        
        # 4. Save to persistent store
        self.save_memory()
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "facts_written": facts_added,
            "timestamp": timestamp
        }

    def check_exists(self, key: str, value: Any, agent_id: Optional[str] = None) -> bool:
        """Checks if a specific fact exists in memory."""
        val_safe = f"'{value}'" if isinstance(value, str) else value
        query_str = f"fact(A, '{key}', {val_safe}, T)"
        if agent_id:
            query_str = f"fact('{agent_id}', '{key}', {val_safe}, T)"
        
        results = list(self.prolog.query(query_str))
        return len(results) > 0

    def query(self, key: str, agent_id: Optional[str] = None):
        """Queries the memory and resolves conflicts using pyDatalog latest-timestamp rules."""
        # 1. Fetch relevant facts from Prolog
        query_str = f"fact(A, '{key}', V, T)"
        if agent_id:
            query_str = f"fact('{agent_id}', '{key}', V, T)"
        
        prolog_results = list(self.prolog.query(query_str))
        if not prolog_results:
            return None
        
        # 2. Load facts into pyDatalog for resolution
        pyDatalog.clear()
        for res in prolog_results:
            # Load as fact_data(Agent, Key, Value, Timestamp)
            + fact_data(str(res['A']), key, res['V'], res['T'])
        
        # 3. Apply resolution rule (latest wins)
        # latest_fact(Key, Value, Agent, Timestamp)
        res_list = latest_fact(key, Y, A, Z)
        
        if res_list:
            # Take the first resolved fact (should be one if timestamps are unique per key)
            resolved = res_list[0]
            # resolved is (key, value, agent, timestamp)
            return {
                "key": resolved[0],
                "value": resolved[1],
                "agent_id": resolved[2],
                "timestamp": resolved[3]
            }
        return None

# Singleton instance
memory_backend = SwarmMemory()

@router.post("/memory/write")
async def write_memory(request: MemoryWriteRequest):
    """
    Writes a payload to the swarm memory. 
    Payload fields are resolved to ontology concepts before being stored.
    """
    return memory_backend.write(request.agent_id, request.protocol, request.payload)

@router.get("/memory/query", response_model=MemoryQueryResponse)
async def query_memory(
    key: str = Query(..., description="The semantic concept name (e.g., 'fullname' or 'price')"),
    agent_id: Optional[str] = Query(None, description="Filter by a specific agent ID (optional)")
):
    """
    Queries the swarm memory for a unified version of a fact.
    Uses PyDatalog rules to resolve conflicts between multiple agents or versions.
    """
    result = memory_backend.query(key, agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Fact not found in memory.")
    return result
