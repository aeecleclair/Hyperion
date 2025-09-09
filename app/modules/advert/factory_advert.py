import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.associations.factory_associations import AssociationsFactory
from app.core.utils.config import Settings
from app.modules.advert import cruds_advert, models_advert
from app.types.factory import Factory


class AdvertFactory(Factory):
    depends_on = [AssociationsFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cruds_advert.create_advert(
            db=db,
            db_advert=models_advert.Advert(
                title="Nouveau mandat",
                content="Nous sommes heureux de vous annoncer notre nouveau mandat !",
                id=uuid.uuid4(),
                date=datetime.now(UTC),
                advertiser_id=AssociationsFactory.association_ids[0],
                post_to_feed=False,
                notification=False,
            ),
        )

        await cruds_advert.create_advert(
            db=db,
            db_advert=models_advert.Advert(
                title="Info M16",
                content="Ne cassez pas les tables svp !",
                id=uuid.uuid4(),
                date=datetime.now(UTC) - timedelta(days=1),
                advertiser_id=AssociationsFactory.association_ids[0],
                post_to_feed=False,
                notification=False,
            ),
        )

        await cruds_advert.create_advert(
            db=db,
            db_advert=models_advert.Advert(
                title="Les 24h du code",
                content="Codons comme des fous !",
                id=uuid.uuid4(),
                date=datetime.now(UTC) - timedelta(days=2),
                advertiser_id=AssociationsFactory.association_ids[1],
                post_to_feed=False,
                notification=False,
            ),
        )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_advert.get_adverts(db=db)) == 0
