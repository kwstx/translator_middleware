from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Enum, ARRAY, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import enum

class ProtocolType(str, enum.Enum):
    A2A = "A2A"
    MCP = "MCP"
    ACP = "ACP"

class ProtocolMapping(SQLModel, table=True):
    __tablename__ = "protocol_mapping"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_protocol: ProtocolType = Field(
        sa_column=Column(Enum(ProtocolType), index=True, nullable=False)
    )
    target_protocol: str = Field(nullable=False)
    mapping_rules: Dict[str, Any] = Field(
        default={}, 
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
    )
    semantic_equivalents: Dict[str, Any] = Field(
        default={}, 
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

class AgentRegistry(SQLModel, table=True):
    __tablename__ = "agent_registry"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), index=True, nullable=False, unique=True)
    )
    supported_protocols: List[str] = Field(
        default=[], 
        sa_column=Column(ARRAY(String))
    )
    capabilities: List[str] = Field(
        default=[],
        sa_column=Column(ARRAY(String))
    )
    semantic_tags: List[str] = Field(
        default=[],
        sa_column=Column(ARRAY(String))
    )
    endpoint_url: str = Field(nullable=False)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

class SemanticOntology(SQLModel, table=True):
    __tablename__ = "semantic_ontology"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str # e.g., "e-commerce-ontology"
    namespace: str # e.g., "http://schema.org/"
    rdf_content: Optional[str] = Field(default=None) # Serialized RDF/XML or Turtle
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
