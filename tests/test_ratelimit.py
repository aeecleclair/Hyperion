from app.dependencies import get_redis_client, get_settings
from app.main import app
from tests.commons import client

settings = app.dependency_overrides.get(get_settings, get_settings)()


def test_limiter():
    app.dependency_overrides.get(get_redis_client, get_redis_client)(
        settings, activate=True
    )
    if settings.REDIS_HOST != "":
        for _ in range(settings.REDIS_LIMIT - 1):
            response = client.get(
                "/health"
            )  # Fake endpoint, we don't care about the response
            assert response.status_code == 404
        response = client.get("/health")
        assert response.status_code == 429


def test_deactivate_limiter():  # We deactivate the limiter to avoid errors in other tests, it is not really a test, but it is needed
    app.dependency_overrides.get(get_redis_client, get_redis_client)(deactivate=True)
