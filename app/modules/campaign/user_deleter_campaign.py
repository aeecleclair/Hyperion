from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.campaign import cruds_campaign, types_campaign
from app.types.module_user_deleter import ModuleUserDeleter


class CampaignUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        status = await cruds_campaign.get_status(db=db)
        if status != types_campaign.StatusType.published:
            return "    - User has voted in unpublished campaign, wait for publish"
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_campaign.delete_user_has_voted(
            db=db,
            user_id=user_id,
        )
