from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Enum, ARRAY, String, text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import enum

class ProtocolType(str, enum.Enum):
    A2A = "A2A"
    MCP = "MCP"
    ACP = "ACP"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    COMPLETED = "COMPLETED"
    DEAD_LETTER = "DEAD_LETTER"

class AgentMessageStatus(str, enum.Enum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    ACKED = "ACKED"
    DEAD_LETTER = "DEAD_LETTER"

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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
    )

class ProtocolVersionDelta(SQLModel, table=True):
    __tablename__ = "protocol_version_delta"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    protocol: ProtocolType = Field(
        sa_column=Column(Enum(ProtocolType), index=True, nullable=False)
    )
    from_version: str = Field(index=True, nullable=False)
    to_version: str = Field(index=True, nullable=False)
    delta_rules: Dict[str, Any] = Field(
        default={},
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
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
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    is_active: bool = Field(default=True)

class SemanticOntology(SQLModel, table=True):
    __tablename__ = "semantic_ontology"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str # e.g., "e-commerce-ontology"
    namespace: str # e.g., "http://schema.org/"
    rdf_content: Optional[str] = Field(default=None) # Serialized RDF/XML or Turtle
    description: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_protocol: str = Field(index=True, nullable=False)
    target_protocol: str = Field(index=True, nullable=False)
    target_agent_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), index=True, nullable=False)
    )
    source_message: Dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False)
    )
    eat: Optional[str] = Field(default=None) # The Engram Access Token used to authorize this task
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        sa_column=Column(Enum(TaskStatus), index=True, nullable=False),
    )
    attempts: int = Field(default=0, nullable=False)
    max_attempts: int = Field(default=5, nullable=False)
    lease_owner: Optional[str] = Field(default=None)
    leased_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    last_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    dead_lettered_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

class AgentMessage(SQLModel, table=True):
    __tablename__ = "agent_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True, nullable=False)
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), index=True, nullable=False)
    )
    payload: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    status: AgentMessageStatus = Field(
        default=AgentMessageStatus.PENDING,
        sa_column=Column(Enum(AgentMessageStatus), index=True, nullable=False),
    )
    attempts: int = Field(default=0, nullable=False)
    max_attempts: int = Field(default=5, nullable=False)
    lease_owner: Optional[str] = Field(default=None)
    leased_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    last_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
    )
    acked_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class MappingFailureLog(SQLModel, table=True):
    __tablename__ = "mapping_failure_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_protocol: str = Field(index=True, nullable=False)
    target_protocol: str = Field(index=True, nullable=False)
    source_field: str = Field(index=True, nullable=False)
    payload_excerpt: Dict[str, Any] = Field(
        default={},
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb")),
    )
    error_type: str = Field(nullable=False)
    model_suggestion: Optional[str] = Field(default=None)
    model_confidence: Optional[float] = Field(default=None)
    applied: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    user_metadata: Dict[str, Any] = Field(
        default={},
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
    )


class PermissionProfile(SQLModel, table=True):
    __tablename__ = "permission_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False, unique=True)
    )
    profile_name: str = Field(default="Standard")
    # Permissions structure: {"tool_id": ["read", "write"], "agent_id": ["execute"]}
    permissions: Dict[str, List[str]] = Field(
        default={},
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
    )

class CredentialType(str, enum.Enum):
    API_KEY = "API_KEY"
    OAUTH_TOKEN = "OAUTH_TOKEN"
    DELEGATED_TOKEN = "DELEGATED_TOKEN"

class ProviderCredential(SQLModel, table=True):
    __tablename__ = "provider_credentials"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    )
    provider_name: str = Field(index=True, nullable=False) # e.g., "claude", "slack"
    credential_type: CredentialType = Field(
        sa_column=Column(Enum(CredentialType), index=True, nullable=False)
    )
    encrypted_token: str = Field(nullable=False)
    
    # Extra data like refresh tokens, expiry for OAuth
    credential_metadata: Dict[str, Any] = Field(
        default={},
        sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)),
    )
