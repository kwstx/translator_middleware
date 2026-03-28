from __future__ import annotations

from pathlib import Path
import sys

from engram_sdk import EngramSDK
from engram_sdk.types import ToolAction, ToolDefinition

_HERE = Path(__file__).resolve().parent
sys.path.append(str(_HERE))
from config import get_agent_id, get_base_url, get_endpoint_url, get_eat


def main() -> None:
    agent_id = get_agent_id()
    base_url = get_base_url()
    endpoint_url = get_endpoint_url()

    sdk = EngramSDK(
        base_url=base_url,
        eat=get_eat(),
        agent_id=agent_id,
        endpoint_url=endpoint_url,
        supported_protocols=["MCP"],
        semantic_tags=["demo", "echo"],
    )

    echo_tool = ToolDefinition(
        name="EchoTool",
        description="Returns whatever payload it receives.",
        version="1.0.0",
        tags=["demo"],
        actions=[
            ToolAction(
                name="echo",
                description="Echo the input payload.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    },
                    "required": ["message"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "echo": {"type": "string"},
                    },
                },
            )
        ],
    )

    sdk.register_tool(echo_tool)

    print("Registering agent and tools with Engram...")
    response = sdk.register_agent()
    print("Registration complete.")
    print(f"Agent ID: {agent_id}")
    print(f"Registry response: {response}")


if __name__ == "__main__":
    main()
