from app.types.module_user_deleter import ModuleUserDeleter


class HomeUserDeleter(ModuleUserDeleter):
    def can_delete_user(self, user_id) -> bool:
        return True

    def delete_user(self, user_id) -> None:
        pass


user_deleter = HomeUserDeleter()
