from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.config import Settings


class Factory(ABC):
    """
    Base class for factories.
    Factories are used to create data in the database.
    Each factory should inherit from this class and implement the `run` and `should_run` methods.
    The `run` method should contain the logic to add data to the database.
    The `should_run` method should contain the logic to check if the factory should run.
    The `depends_on` parameter is a list of factories that should be run before this factory.



    Example:
    ```python

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.types.factory import Factory


    class YourModuleFactory(Factory):
        depends_on = []  # List of factories that should be run before this factory

        @classmethod
        async def run(cls, db: AsyncSession):
                pass

        @classmethod
        async def should_run(cls, db: AsyncSession):
                return True
    ```
    The `should_run` method should return True if the factory should run, and False if it should not.
    """

    depends_on: list[type["Factory"]]

    @classmethod
    @abstractmethod
    async def should_run(cls, db: AsyncSession) -> bool:
        """
        Check if the factory should run.
        This prevent duplicate runs of the same factory as it may cause SQL unique constraint errors or add too much data.
        """

    @classmethod
    @abstractmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        """
        Logic to add data to the database.
        This should be the main logic of the factory.
        """
