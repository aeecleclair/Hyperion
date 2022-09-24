import redis

from app.core.config import Settings


def connect(settings: Settings) -> redis.Redis | bool:
    redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    redis_client.ping()  # Test the connection

    return redis_client


def disconnect(redis_client: redis.Redis) -> None:
    redis_client.close()


def limiter(redis_client: redis.Redis, key: str, limit: int, window: int):
    """Simple fixed window rate limiter, returns a couple  of boolean: the first is True if the request can be processed, False otherwise; the second indicate if an alert should be issued. key should be an ip address or a user id"""
    # Fixed window: see https://konghq.com/blog/how-to-design-a-scalable-rate-limiting-algorithm.
    nb = redis_client.incr(key)
    if nb == 1:
        redis_client.expire(key, window)
    elif nb == limit:
        return (
            False,
            True,
        )  # We want to issue an alert the first time the limit is reached
    elif nb > limit:
        return False, False
    return True, False
