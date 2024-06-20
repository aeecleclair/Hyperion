import pytest
from fastapi.testclient import TestClient

from app.app import get_application
from app.dependencies import get_db, get_redis_client, get_settings
from tests.commons import (
    override_get_db,
    override_get_redis_client,
    override_get_settings,
    settings,
)


@pytest.fixture(scope="module", autouse=True)
def client() -> TestClient:
    test_app = get_application(settings=settings, drop_db=True)  # Create the test's app

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_settings] = override_get_settings
    test_app.dependency_overrides[get_redis_client] = override_get_redis_client

    return TestClient(test_app)  # Create a client to execute tests
