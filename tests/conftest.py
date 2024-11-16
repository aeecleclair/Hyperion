import pytest
from fastapi.testclient import TestClient

from app.app import get_application
from app.dependencies import (
    get_db,
    get_payment_tool,
    get_redis_client,
    get_settings,
    get_unsafe_db,
)
from tests.commons import (
    override_get_db,
    override_get_payment_tool,
    override_get_redis_client,
    override_get_settings,
    override_get_unsafe_db,
    settings,
)


@pytest.fixture(scope="module", autouse=True)
def client() -> TestClient:
    test_app = get_application(settings=settings, drop_db=True)  # Create the test's app

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_unsafe_db] = override_get_unsafe_db
    test_app.dependency_overrides[get_settings] = override_get_settings
    test_app.dependency_overrides[get_redis_client] = override_get_redis_client
    test_app.dependency_overrides[get_payment_tool] = override_get_payment_tool

    return TestClient(test_app)  # Create a client to execute tests
