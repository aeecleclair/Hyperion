from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.flappybird.cruds_flappybird import (
    delete_flappybird_best_score,
    delete_flappybird_score,
)
from app.types.module_user_deleter import ModuleUserDeleter


class FlappybirdUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await delete_flappybird_best_score(
            db=db,
            user_id=user_id,
        )
        await delete_flappybird_score(
            db=db,
            user_id=user_id,
        )
