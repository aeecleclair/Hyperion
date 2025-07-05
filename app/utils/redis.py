import redis


def limiter(redis_client: redis.Redis, key: str, limit: int, window: int):
    """Simple fixed window rate limiter, returns a couple of booleans: the first is True if the request can be processed, False otherwise; the second indicates if an alert should be issued. key should be an ip address or a user id"""
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


def locker_get(redis_client: redis.Redis, key: str):
    value = redis_client.get(key)
    if value is None:
        return False
    return bool(int(value))


def locker_set(redis_client: redis.Redis, key: str, lock: bool):
    redis_client.set(key, int(lock))
