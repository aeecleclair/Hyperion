import logging

from arq.connections import RedisSettings

from app.dependencies import get_settings

scheduler_logger = logging.getLogger("scheduler")


async def run_task(ctx, job_function):
    scheduler_logger.debug(f"Job function consumed {job_function}")
    return await job_function()


settings = get_settings()  # Ce fichier ne doit être lancé que par la prod


class WorkerSettings:
    functions = [run_task]
    allow_abort_jobs = True
    keep_result = 0
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )
