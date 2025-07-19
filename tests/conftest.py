from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.app import get_application
from app.dependencies import (
    get_settings,
    init_app_state,
)
from tests.commons import (
    override_get_settings,
    override_init_app_state,
    settings,
)


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[TestClient, None, None]:
    test_app = get_application(settings=settings, drop_db=True)  # Create the test's app

    test_app.dependency_overrides[init_app_state] = override_init_app_state
    test_app.dependency_overrides[get_settings] = override_get_settings()

    # The TestClient should be used as a context manager in order for the lifespan to be called
    # See https://www.starlette.io/lifespan/#running-lifespan-in-tests
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="module")
def factory_running_client() -> Generator[TestClient, None]:
    """
    This fixture is used to create the FastAPI application instance for testing.
    It sets up the application with the necessary dependencies and configurations.
    """
    test_app = get_application(
        settings=override_get_settings(
            USE_FACTORIES=True,
            FACTORIES_DEMO_USERS_PASSWORD="realpassword",
        )(),
        drop_db=True,
    )
    test_app.dependency_overrides[init_app_state] = override_init_app_state
    test_app.dependency_overrides[get_settings] = override_get_settings(
        USE_FACTORIES=True,
        FACTORIES_DEMO_USERS_PASSWORD="realpassword",
    )

    with TestClient(test_app) as client:
        # Set the base URL for the test client
        yield client
