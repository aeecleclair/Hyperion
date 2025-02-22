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
        pass

    @abstractmethod
    async def run(self, db: AsyncSession):
        pass
