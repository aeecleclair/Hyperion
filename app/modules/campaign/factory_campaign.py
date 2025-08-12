import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.config import Settings
from app.modules.campaign import cruds_campaign, models_campaign
from app.modules.campaign.types_campaign import ListType
from app.types.factory import Factory


class CampaignFactory(Factory):
    depends_on = []

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        section_id = str(uuid.uuid4())
        await cruds_campaign.add_section(
            db=db,
            section=models_campaign.Sections(
                description="Le WEIII",
                name="WEI",
                id=section_id,
                lists=[],
            ),
        )

        await cruds_campaign.add_list(
            db=db,
            campaign_list=models_campaign.Lists(
                description="Go to hawaii",
                name="Haweii",
                program="Plein de trucs trop cool",
                section_id=section_id,
                type=ListType.pipo,
                members=[],
                id=str(uuid.uuid4()),
            ),
        )
        await cruds_campaign.add_list(
            db=db,
            campaign_list=models_campaign.Lists(
                description="On vous emmène au paradis",
                name="StairWEI to HEAVEN",
                program="Programme chargé",
                section_id=section_id,
                type=ListType.serio,
                members=[],
                id=str(uuid.uuid4()),
            ),
        )

        await cruds_campaign.add_section(
            db=db,
            section=models_campaign.Sections(
                description="BDE",
                name="BDE",
                id=str(uuid.uuid4()),
                lists=[],
            ),
        )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_campaign.get_lists(db=db)) == 0
