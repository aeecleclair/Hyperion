# Redis Cache for Ticketing Module

import logging
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel
from redis import Redis


hyperion_error_logger = logging.getLogger("hyperion.error")

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class RedisKeysList:
    """List of Redis keys used in the ticketing module."""

    @staticmethod
    def event_quota(event_id: UUID) -> str:
        return f"ticketing:event:{event_id}:quota"

    @staticmethod
    def category_quota(category_id: UUID) -> str:
        return f"ticketing:category:{category_id}:quota"

    @staticmethod
    def session_quota(session_id: UUID) -> str:
        return f"ticketing:session:{session_id}:quota"


def use_or_set_cache_with_crud(
    redis: Redis,
    key: str,
    crud_func,
    schema_class: type[SchemaT],
    *args,
    **kwargs,
) -> SchemaT:
    """Use cache if available, otherwise call the database function."""
    # If redis is not available, call the crud directly
    if redis is None and not isinstance(redis, Redis):
        return crud_func(*args, **kwargs)
    cached_value = redis.get(key)
    if cached_value is not None:
        try:
            return schema_class.model_validate_json(cached_value)
        except Exception:
            # If cache is corrupted, delete it and call the crud function
            hyperion_error_logger.exception(
                f"Error parsing cache for key {key}, deleting it. Value: {cached_value}"
            )
            redis.delete(key)

    value = crud_func(*args, **kwargs)
    redis.set(key, value.model_dump_json())
    return value


def increment_key(redis: Redis, key: str, amount: int = 1):
    """Increment a Redis key by a given amount."""
    if redis is not None and isinstance(redis, Redis):
        redis.incrby(key, amount)
