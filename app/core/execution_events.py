import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db.models import TaskEvent
import uuid


async def emit_execution_event(
    event_type: str,
    message: str,
    *,
    task_id: Optional[str] = None,
    db: Optional[Any] = None,
    data: Optional[Dict[str, Any]] = None,
    level: str = "info",
) -> None:
    """
    Emit a structured execution event for consumers.
    - Optionally persists to the database for remote clients (CLI).
    """
    payload = {
        "type": event_type,
        "message": message,
        "data": data or {},
        "task_id": str(task_id) if task_id else None,
        "level": level,
        "ts": time.time(),
    }

    # emit_tui_event(payload)  # TUI Purged

    task_uuid = None
    if isinstance(task_id, uuid.UUID):
        task_uuid = task_id
    elif isinstance(task_id, str):
        try:
            task_uuid = uuid.UUID(task_id)
        except ValueError:
            task_uuid = None

    if db and task_uuid:
        event = TaskEvent(
            task_id=task_uuid,
            event_type=event_type,
            message=message,
            data=data or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
