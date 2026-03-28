from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from .exceptions import EngramSDKError
from .types import TaskExecution, TaskResponse


class TaskExecutor:
    """
    High-level task execution interface for tools and agents.
    Polls Engram for tasks, normalizes payloads, and returns structured responses.
    """

    def __init__(
        self,
        sdk: "EngramSDK",
        *,
        agent_id: Optional[str] = None,
        lease_seconds: Optional[int] = None,
    ) -> None:
        self._sdk = sdk
        self._agent_id = agent_id
        self._lease_seconds = lease_seconds

    @property
    def agent_id(self) -> Optional[str]:
        return self._agent_id or self._sdk.agent_id

    def poll(self) -> Optional[TaskExecution]:
        lease = self._sdk.receive_task(
            agent_id=self.agent_id,
            lease_seconds=self._lease_seconds,
        )
        if lease is None:
            return None

        raw_payload = lease.payload or {}
        payload = raw_payload
        metadata: Dict[str, Any] = {
            "message_id": lease.message_id,
            "task_id": lease.task_id,
            "leased_until": lease.leased_until.isoformat(),
        }
        if isinstance(raw_payload, dict) and "task" in raw_payload:
            payload = raw_payload.get("task") or {}
            context = raw_payload.get("context")
            if isinstance(context, dict):
                metadata.update(context)
        return TaskExecution(
            message_id=lease.message_id,
            task_id=lease.task_id,
            payload=payload,
            leased_until=lease.leased_until,
            metadata=metadata,
        )

    def respond(
        self,
        task: TaskExecution,
        response: TaskResponse | Dict[str, Any],
    ) -> Dict[str, Any]:
        if isinstance(response, TaskResponse):
            payload: Dict[str, Any] = {
                "status": response.status,
                "response": response.output or {},
                "error": response.error,
                "response_protocol": response.protocol,
                "metadata": response.metadata,
            }
        elif isinstance(response, dict):
            if "response" not in response and "status" not in response:
                payload = {"status": "success", "response": response}
            elif "response" not in response and "output" in response:
                payload = {
                    "status": response.get("status", "success"),
                    "response": response.get("output") or {},
                    "error": response.get("error"),
                    "response_protocol": response.get("protocol"),
                    "metadata": response.get("metadata") or {},
                }
            else:
                payload = response
        else:
            raise EngramSDKError("Response must be a TaskResponse or dict.")

        return self._sdk.send_response(
            message_id=task.message_id,
            response_payload=payload,
        )

    def run(
        self,
        handler: Callable[[TaskExecution], TaskResponse | Dict[str, Any]],
        *,
        idle_sleep: float = 1.0,
        max_tasks: Optional[int] = None,
    ) -> None:
        processed = 0
        while True:
            task = self.poll()
            if task is None:
                time.sleep(idle_sleep)
                continue

            response = handler(task)
            self.respond(task, response)
            processed += 1

            if max_tasks is not None and processed >= max_tasks:
                return
