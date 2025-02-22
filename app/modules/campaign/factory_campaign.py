import uuid

from app.modules.campaign import cruds_campaign, models_campaign
from app.modules.campaign.types_campaign import ListType
from app.utils.factory import Factory


class CampaignFactory(Factory):
    def __init__(self):
        super().__init__(
            name="campaign",
            depends_on=[],
        )

    async def create_campaign(self, db):
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
                program="T'inquiete frère",
                section_id=section_id,
                type=ListType.pipo,
                members=[],
                id=str(uuid.uuid4()),
            ),
        )
        await cruds_campaign.add_list(
            db=db,
            campaign_list=models_campaign.Lists(
                description="Ok les escaliers c'est cool",
                name="StairWEI to HEAVEN",
                program="T'inquiete frère ++",
                section_id=section_id,
                type=ListType.serio,
                members=[],
                id=str(uuid.uuid4()),
            ),
        )


    async def run(self, db):
        await self.create_campaign(db)

    async def should_run(self, db):
        campaigns = await cruds_campaign.get_lists(db=db)
        return len(campaigns) == 0


factory = CampaignFactory()
