from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.app import get_application
from app.dependencies import (
    get_settings,
    init_state,
)
from tests import commons
from tests.commons import (
    create_test_settings,
    override_get_settings,
    override_init_state,
)


@pytest.fixture(scope="module", autouse=True)
def client(request) -> Generator[TestClient]:
    """
    TestClient fixture.

    A parameter `use_attribute` can be passed to the fixture using:
    ```python
    @pytest.mark.parametrize("client", [True], indirect=True)
    async def test_example(client: TestClient):
        ...
    ```
    """
    try:
        use_factory = request.__getattribute__("param")
    except AttributeError:
        use_factory = False

    commons.SETTINGS = create_test_settings(
        USE_FACTORIES=use_factory,
    )

    test_app = get_application(
        settings=commons.SETTINGS,
        drop_db=True,
    )  # Create the test's app

    test_app.dependency_overrides[init_state] = override_init_state
    test_app.dependency_overrides[get_settings] = override_get_settings

    # The TestClient should be used as a context manager in order for the lifespan to be called
    # See https://www.starlette.io/lifespan/#running-lifespan-in-tests
    with TestClient(test_app) as client:
        yield client
