from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import Enum, ARRAY, String, text, ForeignKey, DateTime, JSON, UUID
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
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    DEAD_LETTER = "DEAD_LETTER"

class AgentMessageStatus(str, enum.Enum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    ACKED = "ACKED"
    DEAD_LETTER = "DEAD_LETTER"

class ProtocolMapping(SQLModel, table=True):
    __tablename__ = "protocol_mapping"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_protocol: ProtocolType = Field(
        sa_column=Column(Enum(ProtocolType), index=True, nullable=False)
    )
    target_protocol: str = Field(index=True, nullable=False)
    mapping_rules: Dict[str, Any] = Field(
        default={}, 
        sa_type=JSON
    )
    semantic_equivalents: Dict[str, Any] = Field(
        default={}, 
        sa_type=JSON
    )
    fidelity_weight: float = Field(default=1.0, nullable=False) # Lower is better, represents data preservation
    version: int = Field(default=1, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProtocolVersionDelta(SQLModel, table=True):
    __tablename__ = "protocol_version_delta"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    protocol: ProtocolType = Field(index=True, nullable=False)
    from_version: str = Field(index=True, nullable=False)
    to_version: str = Field(index=True, nullable=False)
    delta_rules: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentRegistry(SQLModel, table=True):
    __tablename__ = "agent_registry"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(index=True, nullable=False, unique=True)
    supported_protocols: List[str] = Field(
        default=[], 
        sa_type=JSON
    )
    capabilities: List[str] = Field(
        default=[], 
        sa_type=JSON
    )
    semantic_tags: List[str] = Field(
        default=[],
        sa_type=JSON
    )
    endpoint_url: str = Field(nullable=False)
    documentation_url: Optional[str] = Field(default=None) # OpenAPI or documentation URL
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    last_scraped: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    is_active: bool = Field(default=True)
    avg_latency: float = Field(default=0.0, nullable=False) # In seconds
    success_rate: float = Field(default=1.0, nullable=False) # 0.0 to 1.0
    
    tools: List["ToolRegistry"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
        back_populates="agent"
    )


class ToolRegistry(SQLModel, table=True):
    __tablename__ = "tool_registry"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="agent_registry.agent_id", index=True, nullable=False)
    agent: "AgentRegistry" = Relationship(back_populates="tools")
    name: str = Field(index=True, nullable=False)
    description: str = Field(nullable=False)
    version: Optional[str] = None
    tags: List[str] = Field(
        default=[],
        sa_type=JSON
    )
    
    # Detailed actions provided by the tool
    # Example item: {"name": "send", "description": "Send a message", "input_schema": {...}}
    actions: List[Dict[str, Any]] = Field(
        default=[],
        sa_type=JSON
    )
    
    # Schemas for the tool if it acts as a single function
    input_schema: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    output_schema: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    
    # Capability requirements for calling this tool
    required_permissions: List[str] = Field(
        default=[],
        sa_type=JSON
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    execution_metadata: Optional["ToolExecutionMetadata"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
        back_populates="tool"
    )


class ExecutionType(str, enum.Enum):
    MCP = "MCP"
    CLI = "CLI"
    HTTP = "HTTP"


class ToolExecutionMetadata(SQLModel, table=True):
    __tablename__ = "tool_execution_metadata"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tool_id: uuid.UUID = Field(foreign_key="tool_registry.id", index=True, nullable=False, unique=True)
    tool: "ToolRegistry" = Relationship(back_populates="execution_metadata")
    
    execution_type: ExecutionType = Field(index=True, nullable=False)
    
    # Stores spec (OpenAPI/GraphQL), CLI wrapper info, or MCP details
    exec_params: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    
    # Secure storage for CLI wrapper scripts/templates
    cli_wrapper: Optional[str] = Field(default=None)
    
    # Docker config for CLI/Isolated execution
    docker_image: Optional[str] = Field(default=None)
    docker_config: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    
    # Auth mapping: e.g., {"api_key_header": "X-API-Key", "env_vars": {"AUTH_TOKEN": "EAT"}}
    auth_config: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )

    # Recovery strategies (automated or suggested repairs)
    # e.g., [{"error_pattern": "timeout", "action": "retry_with_high_latency_backend"}]
    recovery_strategies: List[Dict[str, Any]] = Field(
        default=[],
        sa_type=JSON
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolRoutingDecision(SQLModel, table=True):
    __tablename__ = "tool_routing_decisions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tool_id: uuid.UUID = Field(foreign_key="tool_registry.id", index=True, nullable=False)
    action: Optional[str] = Field(default=None)
    backend_selected: str = Field(index=True, nullable=False)
    backend_candidates: List[Dict[str, Any]] = Field(
        default=[],
        sa_type=JSON
    )
    task_description: str = Field(nullable=False)
    similarity_score: float = Field(default=0.0, nullable=False)
    performance_score: float = Field(default=0.0, nullable=False)
    composite_score: float = Field(default=0.0, nullable=False)
    token_cost_est: float = Field(default=0.0, nullable=False)
    token_cost_actual: float = Field(default=0.0, nullable=False)
    context_overhead_est: float = Field(default=0.0, nullable=False)
    latency_ms: Optional[float] = Field(default=None)
    success: Optional[bool] = Field(default=None)
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


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
    workflow_id: Optional[uuid.UUID] = Field(default=None, foreign_key="workflows.id", index=True, nullable=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True, nullable=True)
    source_protocol: str = Field(index=True, nullable=False)
    target_protocol: str = Field(index=True, nullable=False)
    target_agent_id: Optional[uuid.UUID] = Field(index=True, nullable=True)
    source_message: Dict[str, Any] = Field(sa_type=JSON)
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results: Optional[Dict[str, Any]] = Field(
        default={},
        sa_type=JSON
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    dead_lettered_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

class Workflow(SQLModel, table=True):
    __tablename__ = "workflows"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(index=True, nullable=False)
    description: Optional[str] = Field(default=None)
    definition: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    eat: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    last_run_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WorkflowSchedule(SQLModel, table=True):
    __tablename__ = "workflow_schedules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workflow_id: uuid.UUID = Field(foreign_key="workflows.id", index=True, nullable=False)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    interval_seconds: int = Field(default=3600, nullable=False)
    enabled: bool = Field(default=True)
    next_run_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), index=True, nullable=False),
    )
    last_run_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskEvent(SQLModel, table=True):
    __tablename__ = "task_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(foreign_key="tasks.id", index=True, nullable=False)
    event_type: str = Field(index=True, nullable=False)
    message: str = Field(nullable=False)
    data: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True),
    )

class EntityState(SQLModel, table=True):
    __tablename__ = "entity_states"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity_key: str = Field(index=True, nullable=False)
    ontology_payload: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    source_id: Optional[str] = Field(default=None, index=True)
    conflict_policy: str = Field(default="last_write_wins", nullable=False)
    version: int = Field(default=1, nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True),
    )

class AgentMessage(SQLModel, table=True):
    __tablename__ = "agent_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(foreign_key="tasks.id", index=True, nullable=False)
    agent_id: uuid.UUID = Field(index=True, nullable=False)
    payload: Dict[str, Any] = Field(sa_type=JSON)
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
        sa_type=JSON
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
        sa_type=JSON
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PermissionProfile(SQLModel, table=True):
    __tablename__ = "permission_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False, unique=True)
    profile_name: str = Field(default="Standard")
    # Permissions structure: {"tool_id": ["read", "write"], "agent_id": ["execute"]}
    permissions: Dict[str, List[str]] = Field(
        default={},
        sa_type=JSON
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CredentialType(str, enum.Enum):
    API_KEY = "API_KEY"
    OAUTH_TOKEN = "OAUTH_TOKEN"
    DELEGATED_TOKEN = "DELEGATED_TOKEN"

class ProviderCredential(SQLModel, table=True):
    __tablename__ = "provider_credentials"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    provider_name: str = Field(index=True, nullable=False) # e.g., "claude", "slack"
    credential_type: CredentialType = Field(index=True, nullable=False)
    encrypted_token: str = Field(nullable=False)
    encrypted_refresh_token: Optional[str] = Field(default=None)
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    
    # Extra data like refresh tokens, expiry for OAuth
    credential_metadata: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TokenAuditEvent(str, enum.Enum):
    ISSUED = "ISSUED"
    REFRESHED = "REFRESHED"
    REVOKED = "REVOKED"


class TokenAuditLog(SQLModel, table=True):
    __tablename__ = "token_audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    token_type: str = Field(index=True, nullable=False)
    event_type: TokenAuditEvent = Field(index=True, nullable=False)
    jti: Optional[str] = Field(default=None, index=True)
    token_hash: str = Field(nullable=False)
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    scopes: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    semantic_scopes: List[str] = Field(
        default=[],
        sa_type=JSON
    )
    extra_metadata: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )


class EvolutionFeedbackType(str, enum.Enum):
    RATING = "RATING"
    CORRECTION = "CORRECTION"
    SUGGESTION = "SUGGESTION"


class ToolFeedback(SQLModel, table=True):
    __tablename__ = "tool_feedback"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tool_id: uuid.UUID = Field(foreign_key="tool_registry.id", index=True, nullable=False)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    eat_token: Optional[str] = Field(index=True) # Token hash or direct EAT
    feedback_type: EvolutionFeedbackType = Field(
        default=EvolutionFeedbackType.RATING,
        sa_column=Column(Enum(EvolutionFeedbackType), index=True, nullable=False),
    )
    score: Optional[float] = Field(default=None) # e.g., 0.0 to 1.0 or -1 to 1
    comment: Optional[str] = Field(default=None)
    metadata_json: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolEvolution(SQLModel, table=True):
    __tablename__ = "tool_evolution"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tool_id: uuid.UUID = Field(foreign_key="tool_registry.id", index=True, nullable=False)
    previous_version: str = Field(nullable=False)
    new_version: str = Field(nullable=False)
    
    # What was changed (semantic diff)
    change_type: str = Field(index=True) # e.g., "description_refinement", "params_optimization"
    diff_payload: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    
    # RL/ML Signals used for this evolution
    evolution_signals: Dict[str, Any] = Field(
        default={},
        sa_type=JSON
    )
    
    confidence_score: float = Field(default=1.0)
    applied_at: Optional[datetime] = Field(default=None) # Set when applied
    applied: bool = Field(default=False) # Whether the change has been applied to registry
    is_active: bool = Field(default=True)
