import logging
import random
import uuid
from datetime import UTC, datetime
from random import randint

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups, groups_type
from app.core.groups.models_groups import CoreMembership
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users
from app.core.users.models_users import CoreUser
from app.core.utils import security
from app.core.utils.config import Settings, UserDemoFactoryConfig
from app.types.factory import Factory
from app.types.floors_type import FloorsType

NB_USERS = 100

faker = Faker("fr_FR")
hyperion_error_logger = logging.getLogger("hyperion.error")


class CoreUsersFactory(Factory):
    demo_users: list[UserDemoFactoryConfig]
    demo_users_id: list[str]

    other_users_id = [str(uuid.uuid4()) for _ in range(NB_USERS)]

    depends_on = []

    @classmethod
    def init_demo_users(cls, settings: Settings) -> None:
        cls.demo_users = (
            settings.FACTORIES_DEMO_USERS
            if settings.FACTORIES_DEMO_USERS
            else [
                UserDemoFactoryConfig(
                    firstname="Alice",
                    name="Dupont",
                    nickname="alice",
                    email="demo1@test.fr",
                    password=Faker().password(16, True, True, True, True),
                ),
                UserDemoFactoryConfig(
                    firstname="Bob",
                    name="Martin",
                    nickname="bob",
                    email="demo2@test.fr",
                    password=Faker().password(16, True, True, True, True),
                ),
            ]
        )
        cls.demo_users_id = [str(uuid.uuid4()) for _ in cls.demo_users]

    @classmethod
    async def create_core_users(cls, db: AsyncSession):
        password = [faker.password(16, True, True, True, True) for _ in range(NB_USERS)]
        firstname = [faker.first_name() for _ in range(NB_USERS)]
        name = [faker.last_name() for _ in range(NB_USERS)]
        nickname = [faker.user_name() for _ in range(NB_USERS)]
        phone = [faker.phone_number() for _ in range(NB_USERS)]
        promos = [
            randint(datetime.now(tz=UTC).year - 5, datetime.now(tz=UTC).year)  # noqa: S311
            for _ in range(NB_USERS)
        ]
        floors = [random.choice(list(FloorsType)) for _ in range(NB_USERS)]  # noqa: S311
        for i in range(NB_USERS):
            hyperion_error_logger.debug(
                "Creating user %s/%s",
                i + 1,
                NB_USERS,
            )
            if i < NB_USERS // 2:
                email = (firstname[i] + "." + name[i] + "@etu.ec-lyon.fr").lower()
                school_id = SchoolType.base_school.value
                account_type = groups_type.AccountType.student
            elif i < 3 * NB_USERS // 4:
                email = (firstname[i] + "." + name[i] + "@ec-lyon.fr").lower()
                school_id = SchoolType.base_school.value
                account_type = groups_type.AccountType.staff
            elif i < 4 * NB_USERS // 5:
                email = (firstname[i] + "." + name[i] + "@centraliens-lyon.net").lower()
                school_id = SchoolType.base_school.value
                account_type = groups_type.AccountType.former_student
            else:
                email = faker.email()
                school_id = SchoolType.no_school.value
                account_type = groups_type.AccountType.external

            user = CoreUser(
                id=cls.other_users_id[i],
                password_hash=password[i],
                firstname=firstname[i],
                nickname=nickname[i],
                name=name[i],
                email=email,
                floor=floors[i],
                phone=phone[i],
                promo=promos[i],
                school_id=school_id,
                account_type=account_type,
                birthday=None,
                created_on=datetime.now(tz=UTC),
            )
            await cruds_users.create_user(db=db, user=user)

        for i, user_info in enumerate(cls.demo_users):
            user = CoreUser(
                id=cls.demo_users_id[i],
                password_hash=security.get_password_hash(
                    user_info.password or faker.password(16, True, True, True, True),
                ),
                firstname=user_info.firstname,
                nickname=user_info.nickname,
                name=user_info.name,
                email=user_info.email,
                floor=None,
                phone=None,
                promo=None,
                school_id=SchoolType.base_school.value,
                account_type=groups_type.AccountType.student,
                birthday=None,
                created_on=datetime.now(tz=UTC),
            )
            await cruds_users.create_user(db=db, user=user)
            for group in user_info.groups:
                await cruds_groups.create_membership(
                    db=db,
                    membership=CoreMembership(
                        group_id=group,
                        user_id=user.id,
                        description=None,
                    ),
                )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        cls.init_demo_users(settings)
        await cls.create_core_users(db=db)

    @classmethod
    async def should_run(cls, db: AsyncSession) -> bool:
        return len(await cruds_users.get_users(db=db)) == 0
