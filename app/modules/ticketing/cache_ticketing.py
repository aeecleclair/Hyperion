# Redis Cache for Ticketing Module

import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar
from uuid import UUID

from pydantic import BaseModel
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ticketing import cruds_ticketing

hyperion_error_logger = logging.getLogger("hyperion.error")

SchemaT = TypeVar("SchemaT", bound=BaseModel)
CrudFuncT = ParamSpec("CrudFuncT")


class RedisKeysList:
    """List of Redis keys used in the ticketing module."""

    @staticmethod
    def event_remaining_quota(event_id: UUID) -> str:
        return f"ticketing:event:{event_id}:quota"

    @staticmethod
    def category_remaining_quota(category_id: UUID) -> str:
        return f"ticketing:category:{category_id}:quota"

    @staticmethod
    def session_remaining_quota(session_id: UUID) -> str:
        return f"ticketing:session:{session_id}:quota"
    
    @staticmethod
    def events() -> str:
        return "ticketing:events"
    
    @staticmethod
    def event(event_id: UUID) -> str:
        return f"ticketing:event:{event_id}"
    
    # @staticmethod
    # def categories(event_id: UUID) -> str:
    #     return f"ticketing:event:{event_id}:categories"

    # @staticmethod
    # def category(category_id: UUID) -> str:
    #     return f"ticketing:category:{category_id}"
    
    # @staticmethod
    # def sessions(category_id: UUID) -> str:
    #     return f"ticketing:category:{category_id}:sessions"

    # @staticmethod
    # def session(session_id: UUID) -> str:
    #     return f"ticketing:session:{session_id}"


async def use_or_set_cache_with_crud(
    redis: Redis | None,
    key: str,
    crud_func: Callable[CrudFuncT, Awaitable[SchemaT]],
    schema_class: type[SchemaT],
    expire: int | None = 300,
    *args: CrudFuncT.args,
    **kwargs: CrudFuncT.kwargs,
) -> SchemaT:
    """Use cache if available, otherwise call the database function."""
    # If redis is not available, call the crud directly
    if redis is None or not isinstance(redis, Redis):
        return await crud_func(*args, **kwargs)
    cached_value: str | bytes | None = redis.get(key)
    if cached_value is not None:
        try:
            return schema_class.model_validate_json(cached_value)
        except Exception:
            # If cache is corrupted, delete it and call the crud function
            hyperion_error_logger.exception(
                "Error parsing cache for key %s, deleting it. Value: %r",
                key,
                cached_value,
            )
            redis.delete(key)

    value = await crud_func(*args, **kwargs)
    redis.set(key, value.model_dump_json(), ex=expire)
    return value


async def use_or_set_cache_with_crud_int(
    redis: Redis | None,
    key: str,
    crud_func: Callable[CrudFuncT, Awaitable[int]],
    expire: int | None = 300,
    *args: CrudFuncT.args,
    **kwargs: CrudFuncT.kwargs,
) -> int:
    """Use cache if available, otherwise call the database function."""
    # If redis is not available, call the crud directly
    if redis is None or not isinstance(redis, Redis):
        return await crud_func(*args, **kwargs)
    cached_value: str | bytes | None = redis.get(key)
    if cached_value is not None:
        try:
            return int(cached_value)
        except Exception:
            # If cache is corrupted, delete it and call the crud function
            hyperion_error_logger.exception(
                "Error parsing cache for key %s, deleting it. Value: %r",
                key,
                cached_value,
            )
            redis.delete(key)

    value = await crud_func(*args, **kwargs)
    redis.set(key, value, ex=expire)
    return value


def increment_key_cache(redis: Redis, key: str, amount: int = 1):
    """Increment a Redis key by a given amount."""
    if redis is not None and isinstance(redis, Redis):
        redis.incrby(key, amount)


def invalidate_key_cache(redis: Redis | None, key: str):
    """Invalidate a Redis cache key."""
    if redis is not None and isinstance(redis, Redis):
        redis.delete(key)


def update_cache_for_new_ticket(
    redis: Redis | None,
    event_id: UUID,
    category_id: UUID,
    session_id: UUID | None,
    amount: int = 1 # Increase the used quota by this amount (default is 1 for a single ticket)
):
    """Update the cache for a new ticket."""
    if redis is not None and isinstance(redis, Redis):
        # Increment the used quota for the event, category, and session
        increment_key_cache(redis, RedisKeysList.event_remaining_quota(event_id), -amount)
        increment_key_cache(redis, RedisKeysList.category_remaining_quota(category_id), -amount)
        if session_id is not None:
            increment_key_cache(redis, RedisKeysList.session_remaining_quota(session_id), -amount)
        # Invalidate the cache for the event, category, and session to ensure consistency
        #invalidate_key_cache(redis, RedisKeysList.events())
        #invalidate_key_cache(redis, RedisKeysList.event(event_id))
        #invalidate_key_cache(redis, RedisKeysList.categories(event_id))
        #invalidate_key_cache(redis, RedisKeysList.category(category_id))
        #invalidate_key_cache(redis, RedisKeysList.sessions(category_id))
        #if session_id is not None:
        #    invalidate_key_cache(redis, RedisKeysList.session(session_id))


async def get_event_remaining_quota_with_cache(
    redis: Redis | None,
    db: AsyncSession,
    event_id: UUID
) -> int | None:
    """Get the remaining quota for an event."""
    return await use_or_set_cache_with_crud_int(
            redis=redis,
            key=RedisKeysList.event_remaining_quota(event_id),
            crud_func=cruds_ticketing.get_event_remaining_quota,
            expire=6*3_600,
            db=db,
            event_id=event_id,
        )


async def get_session_remaining_quota_with_cache(
    redis: Redis | None,
    db: AsyncSession,
    session_id: UUID
) -> int | None:
    """Get the remaining quota for a session."""
    return await use_or_set_cache_with_crud_int(
            redis=redis,
            key=RedisKeysList.session_remaining_quota(session_id),
            crud_func=cruds_ticketing.get_session_remaining_quota,
            expire=6*3_600,
            db=db,
            session_id=session_id,
        )


async def get_category_remaining_quota_with_cache(
    redis: Redis | None,
    db: AsyncSession,
    category_id: UUID
) -> int | None:
    """Get the remaining quota for a category."""
    return await use_or_set_cache_with_crud_int(
            redis=redis,
            key=RedisKeysList.category_remaining_quota(category_id),
            crud_func=cruds_ticketing.get_category_remaining_quota,
            expire=6*3_600,
            db=db,
            category_id=category_id,
        )