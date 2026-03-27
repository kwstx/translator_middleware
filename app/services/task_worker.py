import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Task, TaskStatus, AgentMessage, AgentMessageStatus
from app.db.session import engine
from app.messaging.orchestrator import Orchestrator
from app.services.queue import lease_task
from bridge.router import routeTo

logger = structlog.get_logger(__name__)


class TaskWorker:
    def __init__(
        self,
        poll_interval_seconds: float = settings.TASK_POLL_INTERVAL_SECONDS,
        lease_seconds: int = settings.TASK_LEASE_SECONDS,
        worker_id: Optional[str] = None,
    ):
        self.poll_interval_seconds = poll_interval_seconds
        self.lease_seconds = lease_seconds
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        self._task: Optional[asyncio.Task] = None
        self._orchestrator = Orchestrator()

    async def start(self) -> None:
        if self._task is not None:
            logger.warning("TaskWorker already running", worker_id=self.worker_id)
            return
        self._task = asyncio.create_task(self._run_loop())
        logger.info("TaskWorker started", worker_id=self.worker_id)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("TaskWorker stopped", worker_id=self.worker_id)

    async def _run_loop(self) -> None:
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        while True:
            try:
                async with async_session() as session:
                    task = await lease_task(
                        session,
                        lease_owner=self.worker_id,
                        lease_seconds=self.lease_seconds,
                    )
                    if not task:
                        await asyncio.sleep(self.poll_interval_seconds)
                        continue
                    await self._process_task(session, task)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "TaskWorker loop error", error=str(exc), exc_info=True
                )
                await asyncio.sleep(self.poll_interval_seconds)

    async def _process_task(self, session: AsyncSession, task: Task) -> None:
        now = datetime.now(timezone.utc)
        try:
            await self._orchestrator.translator.refresh_delta_mappings(session)
            # Use reliable routeTo instead of direct handoff
            translated_message = await routeTo(
                target=task.target_protocol,
                payload=task.source_message,
                source_protocol=task.source_protocol,
                correlation_id=str(task.id),
                retry_count=task.attempts,
                eat=task.eat
            )
            message = AgentMessage(
                task_id=task.id,
                agent_id=task.target_agent_id,
                payload=translated_message,
                status=AgentMessageStatus.PENDING,
                max_attempts=settings.AGENT_MESSAGE_MAX_ATTEMPTS,
            )
            session.add(message)
            task.status = TaskStatus.COMPLETED
            task.completed_at = now
            task.lease_owner = None
            task.leased_until = None
            task.updated_at = now
            await session.commit()
        except Exception as exc:
            task.last_error = str(exc)
            task.lease_owner = None
            task.leased_until = None
            if task.attempts >= task.max_attempts:
                task.status = TaskStatus.DEAD_LETTER
                task.dead_lettered_at = now
                dead_payload = {
                    "task_id": str(task.id),
                    "error": str(exc),
                    "source_protocol": task.source_protocol,
                    "target_protocol": task.target_protocol,
                    "source_message": task.source_message,
                }
                session.add(
                    AgentMessage(
                        task_id=task.id,
                        agent_id=task.target_agent_id,
                        payload=dead_payload,
                        status=AgentMessageStatus.DEAD_LETTER,
                        attempts=task.attempts,
                        max_attempts=task.max_attempts,
                        last_error=str(exc),
                    )
                )
            else:
                task.status = TaskStatus.PENDING
            task.updated_at = now
            await session.commit()
