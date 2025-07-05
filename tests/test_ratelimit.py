from fastapi.testclient import TestClient

from tests.commons import settings


def test_limiter(client: TestClient) -> None:
    # Enable the rate limiter for this test
    settings.ENABLE_RATE_LIMITER = True
    try:
        for _ in range(settings.REDIS_LIMIT - 1):
            response = client.get("/information")
            assert response.status_code == 200
        for _ in range(2):
            response = client.get("/information")
            assert response.status_code == 429
    finally:
        settings.ENABLE_RATE_LIMITER = False
