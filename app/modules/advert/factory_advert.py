import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.modules.advert import cruds_advert, models_advert
from app.types.factory import Factory


class AdvertFactory(Factory):
    def __init__(self):
        super().__init__(
            depends_on=[],
        )

    async def run(self, db: AsyncSession):
        advertiser = models_advert.Advertiser(
            id=str(uuid.uuid4()),
            name="Le BDE",
            adverts=[],
            group_manager_id=str(GroupType.BDE.value),
        )

        await cruds_advert.create_advert(
            db=db,
            db_advert=models_advert.Advert(
                title="Nouveau mandat",
                content="Nous sommes heureux de vous annoncer notre nouveau mandat !",
                id=str(uuid.uuid4()),
                date=datetime.now(UTC),
                tags="important",
                advertiser_id=advertiser.id,
                advertiser=advertiser,
            ),
        )

        await cruds_advert.create_advert(
            db=db,
            db_advert=models_advert.Advert(
                title="Info M16",
                content="Ne cassez pas les tables svp !",
                id=str(uuid.uuid4()),
                date=datetime.now(UTC) - timedelta(days=1),
                tags="important",
                advertiser_id=advertiser.id,
                advertiser=advertiser,
            ),
        )

        advertiser2 = models_advert.Advertiser(
            id=str(uuid.uuid4()),
            name="Eclair ces bgs",
            adverts=[],
            group_manager_id=str(GroupType.eclair.value),
        )

        await cruds_advert.create_advert(
            db=db,
            db_advert=models_advert.Advert(
                title="Les 24h du code",
                content="Codons comme des fous !",
                id=str(uuid.uuid4()),
                date=datetime.now(UTC) - timedelta(days=2),
                tags="myecl",
                advertiser_id=advertiser2.id,
                advertiser=advertiser2,
            ),
        )

    async def should_run(self, db: AsyncSession):
        return len(await cruds_advert.get_adverts(db=db)) == 0
