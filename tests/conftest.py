from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.app import get_application
from app.core.payment.types_payment import HelloAssoConfigName
from app.dependencies import (
    get_db,
    get_payment_tool,
    get_redis_client,
    get_scheduler,
    get_settings,
    get_unsafe_db,
    get_websocket_connection_manager,
)
from tests.commons import (
    override_get_db,
    override_get_payment_tool,
    override_get_redis_client,
    override_get_scheduler,
    override_get_settings,
    override_get_unsafe_db,
    override_get_websocket_connection_manager,
)


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[TestClient, None]:
    test_app = get_application(
        settings=override_get_settings()(),
        drop_db=True,
    )
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_unsafe_db] = override_get_unsafe_db
    test_app.dependency_overrides[get_settings] = override_get_settings()
    test_app.dependency_overrides[get_redis_client] = override_get_redis_client
    test_app.dependency_overrides[get_payment_tool(HelloAssoConfigName.CDR)] = (
        override_get_payment_tool(HelloAssoConfigName.CDR)
    )
    test_app.dependency_overrides[get_payment_tool(HelloAssoConfigName.RAID)] = (
        override_get_payment_tool(HelloAssoConfigName.RAID)
    )
    test_app.dependency_overrides[get_payment_tool(HelloAssoConfigName.MYECLPAY)] = (
        override_get_payment_tool(HelloAssoConfigName.MYECLPAY)
    )
    test_app.dependency_overrides[get_scheduler] = override_get_scheduler
    test_app.dependency_overrides[get_websocket_connection_manager] = (
        override_get_websocket_connection_manager
    )

    with TestClient(test_app) as client:
        # Set the base URL for the test client
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
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_unsafe_db] = override_get_unsafe_db
    test_app.dependency_overrides[get_settings] = override_get_settings(
        USE_FACTORIES=True,
        FACTORIES_DEMO_USERS_PASSWORD="realpassword",
    )
    test_app.dependency_overrides[get_redis_client] = override_get_redis_client
    test_app.dependency_overrides[get_payment_tool] = override_get_payment_tool
    test_app.dependency_overrides[get_scheduler] = override_get_scheduler
    test_app.dependency_overrides[get_websocket_connection_manager] = (
        override_get_websocket_connection_manager
    )

    with TestClient(test_app) as client:
        # Set the base URL for the test client
        yield client
