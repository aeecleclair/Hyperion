from fastapi import FastAPI

from app.dependencies import get_db


class Factory:
    def __init__(
        self,
        name: str,
        depends_on: list[str],
        sub_factories: list,
        should_run,
    ) -> None:
        self.name = name
        self.depends_on = depends_on
        self.sub_factories = sub_factories
        self.should_run_test = should_run

    async def should_run(self, app: FastAPI) -> bool:
        async for db in app.dependency_overrides.get(get_db, get_db)():
            return await self.should_run_test(db)

    async def run(self, app: FastAPI):
        async for db in app.dependency_overrides.get(get_db, get_db)():
            for sub_factory in self.sub_factories:
                return await sub_factory(db)
