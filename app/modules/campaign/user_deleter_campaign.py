from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.campaign import cruds_campaign
from app.types.module_user_deleter import ModuleUserDeleter


class CampaignUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        status = await cruds_campaign.get_has_voted(db=db, user_id=user_id)
        if len(status) > 0:
            return "    - User has voted in active campaign, wait for reset"
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_campaign.delete_user_has_voted(
            db=db,
            user_id=user_id,
        )
