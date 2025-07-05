from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.app import get_application
from app.dependencies import (
    get_redis_client,
    get_settings,
    init_app_state,
)
from tests.commons import (
    override_get_redis_client,
    override_get_settings,
    override_init_app_state,
    settings,
)


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[TestClient, None, None]:
    test_app = get_application(settings=settings, drop_db=True)  # Create the test's app

    test_app.dependency_overrides[init_app_state] = override_init_app_state
    test_app.dependency_overrides[get_settings] = override_get_settings
    test_app.dependency_overrides[get_redis_client] = override_get_redis_client

    # The TestClient should be used as a context manager in order for the lifespan to be called
    # See https://www.starlette.io/lifespan/#running-lifespan-in-tests
    with TestClient(test_app) as client:
        yield client
