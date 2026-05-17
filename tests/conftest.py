from collections.abc import Generator
from functools import lru_cache
from unittest.mock import patch

import psycopg
import pytest
import redis
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


@lru_cache(maxsize=1)
def _base_settings():
    """Cached base test settings (no worker-specific overrides), read once per process."""
    return create_test_settings()


def _worker_db_kwargs(worker_id: str) -> dict[str, str]:
    """Return DB-name override kwargs for a given xdist worker ID."""
    if worker_id == "master":
        return {}

    base = _base_settings()

    if base.POSTGRES_DB:
        return {"POSTGRES_DB": f"{base.POSTGRES_DB}_{worker_id}"}

    raise ValueError(  # noqa: TRY003
        "POSTGRES_DB must be set in config.yaml for parallel workers to get isolated databases.",
    )


@pytest.fixture(scope="session", autouse=True)
def worker_database(worker_id: str) -> Generator[None]:
    """Create and tear down a per-worker Postgres DB when running under pytest-xdist."""
    if worker_id == "master":
        yield
        return

    base = _base_settings()

    conn_params = {
        "host": base.POSTGRES_HOST,
        "user": base.POSTGRES_USER,
        "password": base.POSTGRES_PASSWORD,
        "dbname": base.POSTGRES_DB,
    }
    worker_db = f"{base.POSTGRES_DB}_{worker_id}"

    with psycopg.connect(**conn_params, autocommit=True) as conn:
        # Drop first to handle leftover DBs from interrupted previous runs
        conn.execute(f'DROP DATABASE IF EXISTS "{worker_db}"')
        conn.execute(f'CREATE DATABASE "{worker_db}"')

    yield

    with psycopg.connect(**conn_params, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE "{worker_db}" WITH (FORCE)')


@pytest.fixture(scope="module", autouse=True)
def client(request, worker_id: str) -> Generator[TestClient]:
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
        **_worker_db_kwargs(worker_id),
    )

    # init_db is wrapped in a Redis-backed lock (TTL 120s). If the previous
    # test module set the lock, this module's `drop_db=True` would be skipped
    # and stale data would leak between modules. Flush Redis before each module
    # so init_db (and the drop_db it gates) actually runs.
    if commons.SETTINGS.REDIS_HOST:
        try:
            redis.Redis(
                host=commons.SETTINGS.REDIS_HOST,
                port=commons.SETTINGS.REDIS_PORT,
                password=commons.SETTINGS.REDIS_PASSWORD or None,
            ).flushdb()
        except redis.RedisError:
            pass

    test_app = get_application(
        settings=commons.SETTINGS,
        drop_db=True,
    )  # Create the test's app

    test_app.dependency_overrides[init_state] = override_init_state
    test_app.dependency_overrides[get_settings] = override_get_settings

    # The TestClient should be used as a context manager in order for the lifespan to be called
    # See https://www.starlette.io/lifespan/#running-lifespan-in-tests
    #
    # Patch get_number_of_workers to return 1 so that use_lock_for_workers always runs
    # init_db directly. Without this, xdist workers are seen as siblings of the pytest
    # controller's children, causing get_number_of_workers() to return N > 1 and the
    # locking logic to skip init_db on all but one worker, leaving DBs without tables.
    with (
        patch("app.utils.initialization.get_number_of_workers", return_value=1),
        TestClient(test_app) as client,
    ):
        yield client
