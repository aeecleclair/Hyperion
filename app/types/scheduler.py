import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from typing import Any

from arq.jobs import Job

scheduler_logger = logging.getLogger("scheduler")


async def create_scheduler(settings):
    scheduler = Scheduler(settings)
    if scheduler.settings.host != "":
        await scheduler.async_init()
    return scheduler


class Scheduler:
    """Disappears sometimes for no reason"""

    def __init__(self, redis_settings):
        self.settings = redis_settings

    async def async_init(self):
        if self.settings.host != "":
            self.redis_pool = await create_pool(self.settings)
            scheduler_logger.debug(f"Pool in init {self.redis_pool}")

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
        if self.settings.host != "":
            job = await self.redis_pool.enqueue_job(
                "run_task",
                job_function=job_function,
                _job_id=job_id,
                _defer_by=timedelta(seconds=defer_seconds),
            )
            scheduler_logger.debug(f"Job {job_id} queued {job}")
            return job

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
        if self.settings.host != "":
            job = await self.redis_pool.enqueue_job(
                "run_task",
                job_function=job_function,
                _job_id=job_id,
                _defer_until=defer_date,
                **kwargs,
            )
            scheduler_logger.debug(f"Job {job_id} queued {job}")
            return job

    async def cancel_job(self, job_id):
        """
        cancel a queued job based on its job_id
        """
        if self.settings.host != "":
            job = Job(job_id, redis=self.redis_pool)
            scheduler_logger.debug(f"Job aborted {job}")
            await job.abort()
