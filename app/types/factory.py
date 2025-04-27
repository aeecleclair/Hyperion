from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


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
        def __init__(self):
            super().__init__(
                name="module",
                depends_on=[],
            )

        async def run(self, db: AsyncSession):
            pass

        async def should_run(self, db: AsyncSession):
            return True
    ```
    The `should_run` method should return True if the factory should run, and False if it should not.
    """

    def __init__(
        self,
        depends_on: list[type["Factory"]],
    ) -> None:
        """
        Initialize a new Factory object.
        :param depends_on: a list of factories that should be run before this factory
        """
        self.depends_on = depends_on

    @abstractmethod
    async def should_run(self, db: AsyncSession) -> bool:
        """
        Check if the factory should run.
        This prevent duplicate runs of the same factory as it may cause SQL unique constraint errors or add too much data.
        """

    @abstractmethod
    async def run(self, db: AsyncSession) -> None:
        """
        Logic to add data to the database.
        This should be the main logic of the factory.
        """
