import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.pmf import cruds_pmf, models_pmf, types_pmf, schemas_pmf
from app.types.factory import Factory


class PmfFactory(Factory):
    depends_on = [CoreUsersFactory]

    @classmethod
    async def create_offers(cls, db: AsyncSession):
        await cruds_pmf.create_offer(
            offer=schemas_pmf.OfferSimple(
                id=uuid.uuid4(),
                author_id=CoreUsersFactory.demo_users_id[0],
                company_name="Une entreprise quelconque",
                start_date=date(2027, 1, 1),
                duration=6,
                title="Stage 1",
                description="C'est un stage ma foi très intéressant",
                location="Lyon",
                location_type=types_pmf.LocationType.On_site,
                offer_type=types_pmf.OfferType.TFE,
                hidden=True,
            ),
            db=db,
        )
        temp_id=uuid.uuid4()
        await cruds_pmf.create_offer(
            offer=schemas_pmf.OfferSimple(
                id=temp_id,
                author_id=CoreUsersFactory.demo_users_id[1],
                company_name="EDF",
                start_date=date(2026, 12, 12),
                duration=4,
                title="Stage ingénieur",
                description="C'est un deuxième stage",
                location="Ecully",
                location_type=types_pmf.LocationType.On_site,
                offer_type=types_pmf.OfferType.APP,
                hidden=False,
            ),
            db=db,
        )
        await cruds_pmf.create_tag(
            tag=schemas_pmf.TagComplete(
                id=uuid.uuid4(),
                tag="Informatique",
                created_on=datetime.now(UTC).date()
            ),
            db=db,
        )
        await cruds_pmf.create_tag(
            tag=schemas_pmf.TagComplete(
                id=uuid.uuid4(),
                tag="Management",
                created_on=datetime.now(UTC).date()
            ),
            db=db,
        )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.create_offers(db)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        tags = await cruds_pmf.get_tags(db=db)
        return len(tags) == 0
