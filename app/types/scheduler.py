import asyncio
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from datetime import datetime, timedelta
from inspect import iscoroutinefunction, signature
from typing import TYPE_CHECKING, Any

from arq.connections import RedisSettings
from arq.jobs import Job
from arq.typing import WorkerSettingsBase
from arq.worker import create_worker
from fastapi import params

from app import dependencies

if TYPE_CHECKING:
    from arq import Worker
    from sqlalchemy.ext.asyncio import AsyncSession

scheduler_logger = logging.getLogger("scheduler")


async def run_task(
    ctx,
    job_function: Callable[..., Any],
    _dependency_overrides: dict[Callable[..., Any], Callable[..., Any]],
    **kwargs,
):
    """
    Execute the job_function with the provided kwargs

    `job_function` may be a coroutine function or a regular function

    The method will inject the following known dependencies into the job_function if needed:
     - `get_db`
    """
    scheduler_logger.debug(f"Job function consumed {job_function}")

    sign = signature(job_function)
    for param in sign.parameters.values():
        if isinstance(param.default, params.Depends):
            # We iterate over the parameters of the job_function
            # If we find a Depends object, we may want to inject the dependency

            # It is not easy to support any kind of Depends object
            # as the corresponding method may be async or not, or be a special FastAPI object
            # like BackgroundTasks or Request

            # For now we filter accepted Depends objects manually
            # and only accept `get_db`
            if param.default.dependency == dependencies.get_db:
                # `get_db` is the real dependency, defined in dependency.py
                # `_get_db` may be the real dependency or an override
                _get_db: Callable[[], AsyncGenerator[AsyncSession, None]] = (
                    _dependency_overrides.get(
                        dependencies.get_db,
                        dependencies.get_db,
                    )
                )

                async for db in _get_db():
                    kwargs["db"] = db

    if iscoroutinefunction(job_function):
        return await job_function(**kwargs)
    else:
        return job_function(**kwargs)


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
        # self._dependency_overrides: Callable[[], AsyncGenerator[AsyncSession, None]]

    async def start(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str | None,
        _dependency_overrides: dict[Callable[..., Any], Callable[..., Any]],
        **kwargs,
    ):
        """
        Parameters:
        - redis_host: str
        - redis_port: int
        - redis_password: str
        - _dependency_overrides: dict[Callable[..., Any], Callable[..., Any]] a pointer to the app dependency overrides dict
        """

        class ArqWorkerSettings(WorkerSettingsBase):
            functions = [run_task]
            allow_abort_jobs = True
            keep_result_forever = True
            redis_settings = RedisSettings(
                host=redis_host,
                port=redis_port,
                password=redis_password or "",
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

        self._dependency_overrides = _dependency_overrides

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
            _dependency_overrides=self._dependency_overrides,
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
            _dependency_overrides=self._dependency_overrides,
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


class OfflineScheduler(Scheduler):
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

    async def start(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str | None,
        _dependency_overrides: dict[Callable[..., Any], Callable[..., Any]],
        **kwargs,
    ):
        """
        Parameters:
        - redis_host: str
        - redis_port: int
        - redis_password: str
        - _dependency_overrides: dict[Callable[..., Any], Callable[..., Any]] a pointer to the app dependency overrides dict
        """
        self._dependency_overrides = _dependency_overrides

        scheduler_logger.info("OfflineScheduler started")

    async def close(self):
        # If the worker was started, we close it
        pass

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
            f"Job {job_id} queued in OfflineScheduler with defer to {defer_date}",
        )

    async def cancel_job(self, job_id: str):
        """
        cancel a queued job based on its job_id
        """
        scheduler_logger.debug(f"Job {job_id} aborted in OfflineScheduler")
