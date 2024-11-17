import logging
from datetime import timedelta
from uuid import uuid4

from arq import ArqRedis
from arq.jobs import Job

scheduler_logger = logging.getLogger("scheduler")


class Scheduler:
    def __init__(self, redis_pool: ArqRedis):
        self.redis_pool = redis_pool
        scheduler_logger.debug(f"Pool in init {self.redis_pool}")
        self.name = str(uuid4())

    async def queue_job(self, job_function, job_id, defer_time):
        job = await self.redis_pool.enqueue_job(
            "run_task",
            job_function=job_function,
            _job_id=job_id,
            _defer_by=timedelta(seconds=defer_time),
        )
        scheduler_logger.debug(f"Job {job_id} queued {job}")
        return job

    async def cancel_job(self, job_id):
        job = Job(job_id, redis=self.redis_pool)
        scheduler_logger.debug(f"Job aborted {job}")
        await job.abort()
