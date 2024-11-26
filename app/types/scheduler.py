import asyncio
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from arq.connections import RedisSettings
from arq.jobs import Job
from arq.typing import WorkerSettingsBase
from arq.worker import create_worker
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from arq import Worker

scheduler_logger = logging.getLogger("scheduler")


async def run_task(
    ctx,
    job_function: Callable[..., Coroutine[Any, Any, Any]],
    _get_db: Callable[[], AsyncGenerator[AsyncSession, None]],
    **kwargs,
):
    scheduler_logger.debug(f"Job function consumed {job_function}")

    if "db" in kwargs:
        async for db in _get_db():
            kwargs["db"] = db

    return await job_function(**kwargs)


class Scheduler:
    """
    An [arq](https://arq-docs.helpmanual.io/) scheduler.
    The wrapper is intended to be used inside a FastAPI worker.

    The scheduler use a Redis database to store planned jobs.
    """

    # See https://github.com/fastapi/fastapi/discussions/9143#discussioncomment-5157572

    def __init__(self):
        # ArqWorker, in charge of scheduling and executing tasks
        self.worker: Worker | None = None
        # Task will contain the asyncio task that runs the worker
        self.task: asyncio.Task | None = None
        # Pointer to the get_db dependency
        # self._get_db: Callable[[], AsyncGenerator[AsyncSession, None]]

    async def start(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str | None,
        _get_db: Callable[[], AsyncGenerator[AsyncSession, None]],
        **kwargs,
    ):
        """
        Parameters:
        - redis_host: str
        - redis_port: int
        - redis_password: str
        - get_db: Callable[[], AsyncGenerator[AsyncSession, None]] a pointer to `get_db` dependency
        """

        class ArqWorkerSettings(WorkerSettingsBase):
            functions = [run_task]
            allow_abort_jobs = True
            keep_result_forever = True
            redis_settings = RedisSettings(
                host=redis_host,
                port=redis_port,
                password=redis_password if redis_password is not None else "",
            )

        # We pass handle_signals=False to avoid arq from handling signals
        # See https://github.com/python-arq/arq/issues/182
        self.worker = create_worker(
            ArqWorkerSettings,
            handle_signals=False,
            **kwargs,
        )
        # We run the worker in an asyncio task
        self.task = asyncio.create_task(self.worker.async_run())

        self._get_db = _get_db

        scheduler_logger.info("Scheduler started")

    async def close(self):
        # If the worker was started, we close it
        if self.worker is not None:
            await self.worker.close()

    async def queue_job_time_defer(
        self,
        job_function: Callable[..., Coroutine[Any, Any, Any]],
        job_id: str,
        defer_seconds: int,
        **kwargs,
    ):
        """
        Queue a job to execute job_function in defer_seconds amount of seconds
        job_id will allow to abort if needed
        """
        if self.worker is None:
            scheduler_logger.error("Scheduler not started")
            return None
        job = await self.worker.pool.enqueue_job(
            "run_task",
            job_function=job_function,
            _job_id=job_id,
            _defer_by=timedelta(seconds=defer_seconds),
            _get_db=self._get_db,
            **kwargs,
        )
        scheduler_logger.debug(f"Job {job_id} queued {job}")

    async def queue_job_defer_to(
        self,
        job_function: Callable[..., Coroutine[Any, Any, Any]],
        job_id: str,
        defer_date: datetime,
        **kwargs,
    ):
        """
        Queue a job to execute job_function at defer_date
        job_id will allow to abort if needed
        """
        if self.worker is None:
            scheduler_logger.error("Scheduler not started")
            return None
        job = await self.worker.pool.enqueue_job(
            "run_task",
            job_function=job_function,
            _job_id=job_id,
            _defer_until=defer_date,
            _get_db=self._get_db,
            **kwargs,
        )
        scheduler_logger.debug(f"Job {job_id} queued {job}")

    async def cancel_job(self, job_id: str):
        """
        cancel a queued job based on its job_id
        """
        if self.worker is None:
            scheduler_logger.error("Scheduler not started")
            return None
        job = Job(job_id, redis=self.worker.pool)
        scheduler_logger.debug(f"Job aborted {job}")
        await job.abort()


class DummyScheduler(Scheduler):
    """
    A Dummy implementation of the Scheduler to allow to run the server without a REDIS config
    """

    # See https://github.com/fastapi/fastapi/discussions/9143#discussioncomment-5157572

    def __init__(self):
        # ArqWorker, in charge of scheduling and executing tasks
        self.worker: Worker | None = None
        # Task will contain the asyncio task that runs the worker
        self.task: asyncio.Task | None = None
        # Pointer to the get_db dependency
        # self._get_db: Callable[[], AsyncGenerator[AsyncSession, None]]

    async def start(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str | None,
        _get_db: Callable[[], AsyncGenerator[AsyncSession, None]],
        **kwargs,
    ):
        """
        Parameters:
        - redis_host: str
        - redis_port: int
        - redis_password: str
        - get_db: Callable[[], AsyncGenerator[AsyncSession, None]] a pointer to `get_db` dependency
        """
        self._get_db = _get_db

        scheduler_logger.info("DummyScheduler started")

    async def close(self):
        # If the worker was started, we close it
        pass

    async def queue_job_time_defer(
        self,
        job_function: Callable[..., Coroutine[Any, Any, Any]],
        job_id: str,
        defer_seconds: float,
        **kwargs,
    ):
        """
        Queue a job to execute job_function in defer_seconds amount of seconds
        job_id will allow to abort if needed
        """
        scheduler_logger.debug(
            f"Job {job_id} queued in DummyScheduler with defer {defer_seconds} seconds",
        )

    async def queue_job_defer_to(
        self,
        job_function: Callable[..., Coroutine[Any, Any, Any]],
        job_id: str,
        defer_date: datetime,
        **kwargs,
    ):
        """
        Queue a job to execute job_function at defer_date
        job_id will allow to abort if needed
        """
        scheduler_logger.debug(
            f"Job {job_id} queued in DummyScheduler with defer to {defer_date}",
        )

    async def cancel_job(self, job_id: str):
        """
        cancel a queued job based on its job_id
        """
        scheduler_logger.debug(f"Job {job_id} aborted in DummyScheduler")
