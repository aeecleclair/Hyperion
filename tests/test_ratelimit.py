from fastapi.testclient import TestClient

from tests.commons import change_redis_client_status, settings


def test_limiter(client: TestClient) -> None:
    change_redis_client_status(activated=True)
    try:
        for _ in range(settings.REDIS_LIMIT - 1):
            response = client.get("/information")
            assert response.status_code == 200
        for _ in range(2):
            response = client.get("/information")
            assert response.status_code == 429
    finally:
        change_redis_client_status(activated=False)
