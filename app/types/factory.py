from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class Factory(ABC):
    def __init__(
        self,
        name: str,
        depends_on: list[type["Factory"]],
    ) -> None:
        self.name = name
        self.depends_on = depends_on

    @abstractmethod
    async def should_run(self, db: AsyncSession) -> bool:
        """
        Check if the factory should run.
        This prevent duplicate runs of the same factory.
        """

    @abstractmethod
    async def run(self, db: AsyncSession) -> None:
        pass


# Template for a module factory
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.types.factory import Factory


class ModuleFactory(Factory):
    def __init__(self):
        super().__init__(
            name="module",
            depends_on=[],
        )

    async def run(self, db: AsyncSession):
        pass

    async def should_run(self, db: AsyncSession):
        return True


factory = ModuleFactory()
"""
