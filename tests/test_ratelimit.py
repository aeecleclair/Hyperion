from tests.commons import change_redis_client_status, client, settings


def test_limiter():
    change_redis_client_status(activated=True)
    for _ in range(settings.REDIS_LIMIT - 1):
        response = client.get(
            "/health"
        )  # Fake endpoint, we don't care about the response
        assert response.status_code == 404
    response = client.get("/health")
    assert response.status_code == 429
    change_redis_client_status(activated=False)
