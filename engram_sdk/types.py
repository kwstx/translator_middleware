from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolAction:
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    required_permissions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    actions: List[ToolAction] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    required_permissions: List[str] = field(default_factory=list)
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)



@dataclass(frozen=True)
class TaskLease:
    message_id: str
    task_id: str
    payload: Dict[str, Any]
    leased_until: datetime


@dataclass(frozen=True)
class TaskSubmissionResult:
    task_id: str
    status: str
    message: Optional[str] = None
