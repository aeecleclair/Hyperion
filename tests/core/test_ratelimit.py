from fastapi.testclient import TestClient

from tests import commons


def test_limiter(client: TestClient) -> None:
    # Enable the rate limiter for this test

    initial_ENABLE_RATE_LIMITER = commons.SETTINGS.ENABLE_RATE_LIMITER
    commons.SETTINGS.ENABLE_RATE_LIMITER = True
    try:
        for _ in range(commons.SETTINGS.REDIS_LIMIT - 1):
            response = client.get("/information")
            assert response.status_code == 200
        for _ in range(2):
            response = client.get("/information")
            assert response.status_code == 429
    finally:
        commons.SETTINGS.ENABLE_RATE_LIMITER = initial_ENABLE_RATE_LIMITER
