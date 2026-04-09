import asyncio
import uuid
import time
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
from app.core.metrics import record_task_start, record_task_completion
from app.core.logging import bind_context, unbind_context
from app.core.security import verify_engram_token

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
        self._orchestrator_instance = None

    @property
    def orchestrator(self) -> Orchestrator:
        if self._orchestrator_instance is None:
            self._orchestrator_instance = Orchestrator()
        return self._orchestrator_instance

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
                    
                    # Extract user_id from EAT if possible for metrics
                    user_id = "unknown"
                    try:
                        if task.eat:
                            payload = verify_engram_token(task.eat)
                            user_id = str(payload.get("sub", "unknown"))
                    except:
                        pass
                        
                    bind_context(task_id=str(task.id), user_id=user_id, worker_id=self.worker_id)
                    logger.info("Task leased", task_type=task.target_protocol)
                    record_task_start(task.target_protocol, user_id)
                    
                    start_time = time.time()
                    try:
                        await self._process_task(session, task)
                        duration = time.time() - start_time
                        record_task_completion(task.target_protocol, user_id, "success", duration)
                        logger.info("Task completed successfully", duration=duration)
                    except Exception as e:
                        duration = time.time() - start_time
                        record_task_completion(task.target_protocol, user_id, "failure", duration)
                        logger.error("Task failed", error=str(e), duration=duration)
                        # Re-raise or handle in _process_task? _process_task already handles commit and status update
                    finally:
                        unbind_context("task_id", "user_id")

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
            await self.orchestrator.translator.refresh_delta_mappings(session)
            if task.target_protocol == "MULTI_AGENT":
                logger.debug("Executing multi-agent orchestration task")
                from app.messaging.multi_agent_orchestrator import MultiAgentOrchestrator
                multi_orch = MultiAgentOrchestrator(orchestrator=self.orchestrator)
                
                # Extract original command and plan if available
                source_msg = task.source_message or {}
                command = source_msg.get("command", "")
                plan = source_msg.get("plan")
                
                # Execute multi-agent task (it handles status updates to RUNNING/COMPLETED/DEAD_LETTER internally)
                await multi_orch.execute_task(
                    user_task=command,
                    eat=task.eat,
                    db=session,
                    task_id=task.id,
                    plan=plan
                )
                return

            # Legacy/Single-hop translation flow
            translated_message = await routeTo(
                target=task.target_protocol,
                payload=task.source_message,
                source_protocol=task.source_protocol,
                correlation_id=str(task.id),
                retry_count=task.attempts,
                eat=task.eat,
                db=session
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
            raise # Re-raise to let the caller log it properly
