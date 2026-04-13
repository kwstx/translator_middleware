from .client import EngramSDK
from .scope import Scope, ScopeCache
from .types import ToolDefinition, TaskLease, TaskSubmissionResult, TaskExecution, TaskResponse, TranslationResponse, MappingSuggestion
from .execution import TaskExecutor
from .adapter import RuntimeAdapter, ScopeValidationError
from .exceptions import (
    EngramSDKError,
    EngramAuthError,
    EngramRequestError,
    EngramResponseError,
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
]

