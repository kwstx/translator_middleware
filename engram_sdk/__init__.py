from .client import EngramSDK
from .scope import Scope, ScopeCache
from .types import ToolDefinition, TaskLease, TaskSubmissionResult, TaskExecution, TaskResponse, TranslationResponse, MappingSuggestion
from .execution import TaskExecutor
from .adapter import RuntimeAdapter, ScopeValidationError
from .control_plane import ControlPlane
from .exceptions import (
    EngramSDKError,
    EngramAuthError,
    EngramRequestError,
    EngramResponseError,
)
from .global_data import GlobalData, get_global_data, delete_data, DELETE_DATA_TOOL
from .controlled_tools import (
    PROCESS_IDENTITY_TOOL,
    VERIFY_CLEARANCE_TOOL,
    GENERATE_REPORT_TOOL,
    SCRUB_DATA_TOOL,
    process_raw_identification,
    verify_security_clearance,
    generate_access_report,
    scrub_sensitive_data
)

from typing import List, Optional

def scope(name: str, tools: Optional[List[str]] = None, sdk: Optional[EngramSDK] = None) -> Scope:
    """
    Convenience method to create and activate a tool scope.
    If no SDK instance is provided, a default EngramSDK() will be used.
    """
    if sdk is None:
        sdk = EngramSDK()
    return sdk.scope(name, tools=tools)

__all__ = [
    "EngramSDK",
    "Scope",
    "scope",
    "ControlPlane",
    "ScopeCache",
    "ToolDefinition",
    "TaskLease",
    "TaskSubmissionResult",
    "TaskExecution",
    "TaskResponse",
    "TaskExecutor",
    "TranslationResponse",
    "MappingSuggestion",
    "EngramSDKError",
    "ScopeValidationError",
    "RuntimeAdapter",
    "EngramAuthError",
    "EngramRequestError",
    "EngramResponseError",
    "GlobalData",
    "get_global_data",
    "PROCESS_IDENTITY_TOOL",
    "VERIFY_CLEARANCE_TOOL",
    "GENERATE_REPORT_TOOL",
    "DELETE_DATA_TOOL",
    "SCRUB_DATA_TOOL",
    "process_raw_identification",
    "verify_security_clearance",
    "generate_access_report",
    "delete_data",
    "scrub_sensitive_data"
]

