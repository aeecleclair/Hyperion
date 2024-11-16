import logging

scheduler_logger = logging.getLogger("scheduler")


async def run_task(ctx, job_function):
    scheduler_logger.debug(f"Job function consumed {job_function}")
    return await job_function()


class WorkerSettings:
    functions = [run_task]
    allow_abort_jobs = True
    keep_result = 0
