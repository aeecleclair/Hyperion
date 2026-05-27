import random
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schools.factory_schools import CoreSchoolsFactory
from app.core.schools.schools_type import SchoolType
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
    types_sport_competition,
)
from app.types.factory import Factory


class SportCompetitionFactory(Factory):
    depends_on = [
        CoreUsersFactory,
        CoreSchoolsFactory,
    ]  # List of factories that should be run before this factory

    edition_id = uuid4()
    team_sport_id = uuid4()
    team_sport_team_id = uuid4()
    individual_sport_id = uuid4()
    individual_sport_team_id = uuid4()

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cruds_sport_competition.add_edition(
            schemas_sport_competition.CompetitionEdition(
                id=cls.edition_id,
                name="Hyperion Games",
                year=2025,
                start_date=datetime.now(UTC).replace(month=1, day=1),
                end_date=datetime.now(UTC).replace(month=12, day=31),
                active=True,
                inscription_enabled=True,
            ),
            db,
        )
        await cruds_sport_competition.add_school(
            schemas_sport_competition.SchoolExtensionBase(
                school_id=CoreSchoolsFactory.school_id,
                from_lyon=True,
                active=True,
                inscription_enabled=True,
            ),
            db,
        )
        await cruds_sport_competition.add_sport(
            schemas_sport_competition.Sport(
                id=cls.team_sport_id,
                name="Football",
                sport_category=None,
                team_size=10,
                substitute_max=5,
                active=True,
            ),
            db,
        )

        await cruds_sport_competition.add_sport(
            schemas_sport_competition.Sport(
                id=cls.individual_sport_id,
                name="Escrime",
                sport_category=None,
                team_size=1,
                substitute_max=0,
                active=True,
            ),
            db,
        )
        await cls.add_competition_users(db)
        await cls.add_product(db)

    @classmethod
    async def add_competition_users(
        cls,
        db: AsyncSession,
    ) -> None:
        for i, user_id in enumerate(CoreUsersFactory.other_users_id[:13]):
            extra = random.choice([None, "cameraman", "fanfare", "pompom"])  # noqa: S311
            await cruds_sport_competition.add_competition_user(
                schemas_sport_competition.CompetitionUserSimple(
                    user_id=user_id,
                    sport_category=types_sport_competition.SportCategory.masculine,
                    edition_id=cls.edition_id,
                    validated=False,
                    is_athlete=True,
                    is_cameraman=extra == "cameraman",
                    is_fanfare=extra == "fanfare",
                    is_pompom=extra == "pompom",
                    created_at=datetime.now(UTC),
                ),
                db,
            )
            if i == 0:
                await cruds_sport_competition.add_team(
                    schemas_sport_competition.Team(
                        id=cls.team_sport_team_id,
                        name="Team Football",
                        sport_id=cls.team_sport_id,
                        edition_id=cls.edition_id,
                        school_id=SchoolType.centrale_lyon.value,
                        captain_id=user_id,
                        created_at=datetime.now(UTC),
                    ),
                    db,
                )
            if i < 10:
                await cruds_sport_competition.add_participant(
                    schemas_sport_competition.Participant(
                        user_id=user_id,
                        sport_id=cls.team_sport_id,
                        edition_id=cls.edition_id,
                        school_id=SchoolType.centrale_lyon.value,
                        license=f"LICENSE-{i + 1}",
                        substitute=False,
                        is_license_valid=True,
                        team_id=cls.team_sport_team_id,
                    ),
                    db,
                )
            elif i < 12:
                await cruds_sport_competition.add_participant(
                    schemas_sport_competition.Participant(
                        user_id=user_id,
                        sport_id=cls.team_sport_id,
                        edition_id=cls.edition_id,
                        school_id=SchoolType.centrale_lyon.value,
                        license=f"LICENSE-{i + 1}",
                        substitute=True,
                        is_license_valid=True,
                        team_id=cls.team_sport_team_id,
                    ),
                    db,
                )
            else:
                await cruds_sport_competition.add_team(
                    schemas_sport_competition.Team(
                        id=cls.individual_sport_team_id,
                        name="Team Escrime individuel",
                        sport_id=cls.individual_sport_id,
                        edition_id=cls.edition_id,
                        school_id=SchoolType.centrale_lyon.value,
                        captain_id=user_id,
                        created_at=datetime.now(UTC),
                    ),
                    db,
                )
                await cruds_sport_competition.add_participant(
                    schemas_sport_competition.Participant(
                        user_id=user_id,
                        sport_id=cls.individual_sport_id,
                        edition_id=cls.edition_id,
                        school_id=SchoolType.centrale_lyon.value,
                        license=f"LICENSE-{i + 1}",
                        substitute=False,
                        is_license_valid=True,
                        team_id=cls.individual_sport_team_id,
                    ),
                    db,
                )

    @classmethod
    async def add_product(
        cls,
        db: AsyncSession,
    ) -> None:
        product_id = uuid4()
        await cruds_sport_competition.add_product(
            schemas_sport_competition.Product(
                id=product_id,
                name="Light Package",
                description="Description of product 1",
                edition_id=cls.edition_id,
                required=True,
            ),
            db,
        )
        await cruds_sport_competition.add_product_variant(
            schemas_sport_competition.ProductVariant(
                id=uuid4(),
                edition_id=cls.edition_id,
                name="With T-shirt centrale",
                description="Description of product variant for centrale",
                price=2000,
                product_id=product_id,
                unique=True,
                school_type=types_sport_competition.ProductSchoolType.centrale,
                public_type=None,
            ),
            db,
        )
        await cruds_sport_competition.add_product_variant(
            schemas_sport_competition.ProductVariant(
                id=uuid4(),
                edition_id=cls.edition_id,
                name="With T-shirt lyon",
                description="Description of product variant for lyon",
                price=2400,
                product_id=product_id,
                unique=True,
                school_type=types_sport_competition.ProductSchoolType.from_lyon,
                public_type=None,
            ),
            db,
        )
        await cruds_sport_competition.add_product_variant(
            schemas_sport_competition.ProductVariant(
                id=uuid4(),
                edition_id=cls.edition_id,
                name="With T-shirt lyon",
                description="Description of product variant for others",
                price=2500,
                product_id=product_id,
                unique=True,
                school_type=types_sport_competition.ProductSchoolType.others,
                public_type=None,
            ),
            db,
        )

        product2_id = uuid4()
        await cruds_sport_competition.add_product(
            schemas_sport_competition.Product(
                id=product2_id,
                name="Full Package",
                description="Description of product 2",
                edition_id=cls.edition_id,
                required=True,
            ),
            db,
        )
        await cruds_sport_competition.add_product_variant(
            schemas_sport_competition.ProductVariant(
                id=uuid4(),
                edition_id=cls.edition_id,
                name="With T-shirt lyon",
                description="Description of product variant for others",
                price=2500,
                product_id=product2_id,
                unique=True,
                school_type=types_sport_competition.ProductSchoolType.others,
                public_type=None,
            ),
            db,
        )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return await cruds_sport_competition.load_all_editions(db) == []
