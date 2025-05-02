from fastapi.testclient import TestClient

from app.module import all_modules
from tests.commons import TestingSessionLocal


async def test_factories(factory_running_client: TestClient) -> None:
    async with TestingSessionLocal() as db:
        factories = [
            module.factory for module in all_modules if module.factory is not None
        ]
        for factory in factories:
            assert not await factory.should_run(
                db,
            ), f"Factory {factory.__class__.__name__} should not run"
