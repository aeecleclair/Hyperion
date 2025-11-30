from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class ModuleUserDeleter(ABC):
    """
    Abstract base class for user deletion functionality.
    This class defines the interface for deleting users from the system.
    Each module should implement this interface to provide its own user deletion logic.
    """

    @abstractmethod
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        """
        Check if the user can be deleted.
        :param user_id: The ID of the user to check.
        :return: True if the user can be deleted, False otherwise.
        """

    @abstractmethod
    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        """
        Delete the user from the system.
        :param user_id: The ID of the user to delete.
        """


"""
from app.types.module_user_deleter import ModuleUserDeleter

from sqlalchemy.ext.asyncio import AsyncSession


class CoreUserDeleter(ModuleUserDeleter):
    async def can_delete_user(self, user_id: str, db: AsyncSession) -> Literal[True] | str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass


()
"""
