import uuid
from typing import List, Optional, Dict, Any


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

    @property
    def tool_count(self) -> int:
        """Returns the number of tools in this scope."""
        return len(self.tools)

    def contains(self, tool_id: str) -> bool:
        """Checks if a specific tool is included in this scope."""
        return tool_id in self.tools

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Scope to a dictionary representation."""
        return {
            "step_id": self.step_id,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scope":
        """Creates a Scope instance from a dictionary."""
        return cls(
            tools=data.get("tools", []),
            step_id=data.get("step_id"),
        )

    def __repr__(self) -> str:
        return f"Scope(step_id={self.step_id!r}, tools={self.tools!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Scope):
            return NotImplemented
        return self.step_id == other.step_id and self.tools == other.tools
