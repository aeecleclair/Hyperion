import uuid
from datetime import UTC, datetime, timedelta

from app.modules.advert import cruds_advert, models_advert
from app.utils.factory import Factory


class AdvertFactory(Factory):
    def __init__(self):
        super().__init__(
            name="advert",
            depends_on=[],
        )

    async def create_advert(self, db):
        advertiser = models_advert.Advertiser(
            id=str(uuid.uuid4()),
            name="Le BDE",
            adverts=[],
            group_manager_id=str(uuid.uuid4()),
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
                content="Ne casser pas les tables svp !",
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
            group_manager_id=str(uuid.uuid4()),
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

    async def run(self, db):
        await self.create_advert(db)

    async def should_run(self, db):
        adverts = await cruds_advert.get_adverts(db=db)
        return len(adverts) == 0


factory = AdvertFactory()
