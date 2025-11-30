import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.myeclpay.factory_myeclpay import MyECLPayFactory
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.ticketing import cruds_ticketing, schemas_ticketing
from app.types.factory import Factory


class TicketingFactory(Factory):
    depends_on = [
        CoreUsersFactory,
        MyECLPayFactory,
    ]

    event_id = uuid4()
    session1_id = uuid4()
    session2_id = uuid4()
    category1_id = uuid4()
    category2_id = uuid4()
    category3_id = uuid4()

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.add_event(db)
        await cls.add_sessions(db)
        await cls.add_categories(db)
        await cls.add_tickets(db)

    @classmethod
    async def add_event(cls, db: AsyncSession) -> None:
        """Create a sample event."""
        await cruds_ticketing.create_event(
            db,
            schemas_ticketing.EventSimple(
                id=cls.event_id,
                store_id=MyECLPayFactory.other_stores_id[0],
                creator_id=CoreUsersFactory.other_users_id[0],
                name="Commuz 2025",
                open_date=datetime.now(UTC),
                close_date=datetime.now(UTC) + timedelta(days=30),
                quota=500,
                user_quota=4,
                used_quota=0,
                disabled=False,
            ),
        )

    @classmethod
    async def add_sessions(cls, db: AsyncSession) -> None:
        """Create sample sessions."""
        await cruds_ticketing.create_session(
            db,
            schemas_ticketing.SessionBase(
                id=cls.session1_id,
                event_id=cls.event_id,
                name="Session du Samedi Soir",
                quota=300,
                user_quota=2,
                used_quota=0,
                disabled=False,
            ),
        )
        await cruds_ticketing.create_session(
            db,
            schemas_ticketing.SessionBase(
                id=cls.session2_id,
                event_id=cls.event_id,
                name="Session du Dimanche Après-midi",
                quota=200,
                user_quota=2,
                used_quota=0,
                disabled=False,
            ),
        )

    @classmethod
    async def add_categories(cls, db: AsyncSession) -> None:
        """Create sample categories."""
        await cruds_ticketing.create_category(
            db,
            schemas_ticketing.CategoryBase(
                id=cls.category1_id,
                event_id=cls.event_id,
                name="Étudiant Centrale",
                linked_sessions=[cls.session1_id, cls.session2_id],
                required_mebership=["centrale_student"],
                quota=150,
                user_quota=2,
                used_quota=0,
                price=1500,
                disabled=False,
            ),
        )
        await cruds_ticketing.create_category(
            db,
            schemas_ticketing.CategoryBase(
                id=cls.category2_id,
                event_id=cls.event_id,
                name="Étudiant Lyon",
                linked_sessions=[cls.session1_id, cls.session2_id],
                required_mebership=["student"],
                quota=200,
                user_quota=2,
                used_quota=0,
                price=2000,
                disabled=False,
            ),
        )
        await cruds_ticketing.create_category(
            db,
            schemas_ticketing.CategoryBase(
                id=cls.category3_id,
                event_id=cls.event_id,
                name="Externe",
                linked_sessions=[cls.session1_id],
                required_mebership=None,
                quota=100,
                user_quota=1,
                used_quota=0,
                price=3000,
                disabled=False,
            ),
        )

    @classmethod
    async def add_tickets(cls, db: AsyncSession) -> None:
        """Create sample tickets for users."""
        categories = [cls.category1_id, cls.category2_id]

        for _i, user_id in enumerate(CoreUsersFactory.other_users_id[:10]):
            category_id = random.choice(categories)  # noqa: S311

            await cruds_ticketing.create_ticket(
                db,
                schemas_ticketing.TicketSimple(
                    id=uuid4(),
                    user_id=user_id,
                    event_id=cls.event_id,
                    category_id=category_id,
                    total=1500 if category_id == cls.category1_id else 2000,
                    created_at=datetime.now(UTC),
                ),
            )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return await cruds_ticketing.get_events(db) == []
