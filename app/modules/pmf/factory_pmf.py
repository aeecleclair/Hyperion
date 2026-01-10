from app.types.factory import Factory
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.pmf import cruds_pmf,models_pmf,types_pmf
import uuid
from datetime import date

class PmfFactory(Factory):
    depends_on = [CoreUsersFactory]

    @classmethod
    async def create_offers(cls, db: AsyncSession):
        await cruds_pmf.create_offer(
            offer=models_pmf.PmfOffer(
                id=uuid.uuid4(),
                author_id=CoreUsersFactory.demo_users_id[0],
                company_name="Centrale Innovation",
                start_date=date(2025,12,1),
                end_date=date(2026,4,17),
                duration=0,
                title="Stage",
                description="Stageant",
                location="Montcuq",
                location_type=types_pmf.LocationType.On_site,
                offer_type=types_pmf.OfferType.TFE,
                created_at=date.today
            ),
            db=db,
        )
        await cruds_pmf.create_offer(
            offer=models_pmf.PmfOffer(
                id=uuid.uuid4(),
                author_id=CoreUsersFactory.demo_users_id[1],
                company_name="EDF",
                start_date=date(2025,12,12),
                end_date=date(2026,6,5),
                duration=0,
                title="Ingeneirue",
                description="elec",
                location="Ecully",
                location_type=types_pmf.LocationType.On_site,
                offer_type=types_pmf.OfferType.CDI,
                created_at=date.today
            ),
            db=db,
        )


    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.create_offers(db)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        assos = await cruds_pmf.get_offers(db=db)
        return len(assos) == 0
