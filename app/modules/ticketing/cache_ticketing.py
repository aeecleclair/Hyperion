# Redis Cache for Ticketing Module

from uuid import UUID

from redis import Redis

# TODO: Detect redis instance or skip caching if not available


def use_cache_or_else_db(
    redis: Redis,
    key: str,
    db_func,
    *args,
    **kwargs,
):
    """Use cache if available, otherwise call the database function."""
    cached_value = redis.get(key)
    if cached_value is not None:
        return int(cached_value)
    value = db_func(*args, **kwargs)
    redis.set(key, value)
    return value


def increment_quota_event(
    redis: Redis,
    event_id: UUID,
    amount: int = 1,
) -> None:
    """Increment the quota for an event."""
    redis.incrby(f"ticketing:event:{event_id}:quota", amount)

def increment_quota_category(
    redis: Redis,
    category_id: UUID,
    amount: int = 1,
) -> None:
    """Increment the quota for a category."""
    redis.incrby(f"ticketing:category:{category_id}:quota", amount)

def increment_quota_session(
    redis: Redis,
    session_id: UUID,
    amount: int = 1,
) -> None:
    """Increment the quota for a session."""
    redis.incrby(f"ticketing:session:{session_id}:quota", amount)
