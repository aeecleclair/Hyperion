import logging

from arq.connections import RedisSettings

from app.dependencies import get_scheduler, get_settings

scheduler_logger = logging.getLogger("scheduler")


async def run_task(ctx, job_function):
    scheduler_logger.debug(f"Job function consumed {job_function}")
    return await job_function()


settings = get_settings()  # Ce fichier ne doit être lancé que par la prod


class WorkerSettings:
    functions = [run_task]
    allow_abort_jobs = True
    keep_result_forever = True
    redis_pool = get_scheduler().redis_pool
