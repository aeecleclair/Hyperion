from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sport_competition import cruds_sport_competition
from app.types.module_user_deleter import ModuleUserDeleter


class SportCompetitionUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        edition = await cruds_sport_competition.load_active_edition(db)
        if edition is not None and edition.end_date >= datetime.now(tz=UTC):
            competition_user = (
                await cruds_sport_competition.load_competition_user_by_id(
                    user_id,
                    edition.id,
                    db,
                )
            )
            if competition_user is not None:
                return "    - User is registered in an active sport competition edition"
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass
