import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.factory_groups import CoreGroupsFactory
from app.core.utils.config import Settings
from app.modules.advert import cruds_advert, models_advert
from app.types.factory import Factory


class AdvertFactory(Factory):
    depends_on = [CoreGroupsFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        advertiser = models_advert.Advertiser(
            id=str(uuid.uuid4()),
            name="Le BDE",
            adverts=[],
            group_manager_id=CoreGroupsFactory.groups_ids[0],
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
            group_manager_id=CoreGroupsFactory.groups_ids[1],
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

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_advert.get_adverts(db=db)) == 0
