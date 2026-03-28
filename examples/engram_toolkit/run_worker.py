from __future__ import annotations

from pathlib import Path
import sys

from engram_sdk import EngramSDK
from engram_sdk.types import TaskResponse

_HERE = Path(__file__).resolve().parent
sys.path.append(str(_HERE))
from config import get_agent_id, get_base_url, get_eat


def handle_task(task):
    print("Received task payload:")
    print(task.payload)

    output = {
        "handled_by": "EchoTool",
        "original_payload": task.payload,
    }
    return TaskResponse(status="success", output=output, protocol="MCP")


def main() -> None:
    sdk = EngramSDK(
        base_url=get_base_url(),
        eat=get_eat(),
        agent_id=get_agent_id(),
        supported_protocols=["MCP"],
    )

    executor = sdk.task_executor()
    print("Polling for tasks (Ctrl+C to stop)...")
    executor.run(handle_task, idle_sleep=1.0)


if __name__ == "__main__":
    main()
