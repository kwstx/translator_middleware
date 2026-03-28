from __future__ import annotations

from pathlib import Path
import sys

from engram_sdk import EngramSDK

_HERE = Path(__file__).resolve().parent
sys.path.append(str(_HERE))
from config import get_agent_id, get_base_url, get_eat


def main() -> None:
    sdk = EngramSDK(
        base_url=get_base_url(),
        eat=get_eat(),
    )

    source_message = {
        "id": "task_001",
        "payload": {
            "intent": "echo_message",
            "message": "Hello from Engram!",
        },
        "data": {
            "task": "demo_echo"
        },
    }

    result = sdk.tasks.enqueue_task(
        source_message=source_message,
        source_protocol="A2A",
        target_protocol="MCP",
        target_agent_id=get_agent_id(),
    )

    print("Task enqueued.")
    print(result)


if __name__ == "__main__":
    main()
