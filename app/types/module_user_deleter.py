from abc import ABC, abstractmethod


class ModuleUserDeleter(ABC):
    """
    Abstract base class for user deletion functionality.
    This class defines the interface for deleting users from the system.
    Each module should implement this interface to provide its own user deletion logic.
    """

    @abstractmethod
    def can_delete_user(self, user_id) -> bool:
        """
        Check if the user can be deleted.
        :param user_id: The ID of the user to check.
        :return: True if the user can be deleted, False otherwise.
        """

    @abstractmethod
    def delete_user(self, user_id) -> None:
        """
        Delete the user from the system.
        :param user_id: The ID of the user to delete.
        """


"""
from app.types.module_user_deleter import ModuleUserDeleter


class CoreUserDeleter(ModuleUserDeleter):
    def can_delete_user(self, user_id) -> bool:
        return True

    def delete_user(self, user_id) -> None:
        pass


user_deleter = CoreUserDeleter()
"""
