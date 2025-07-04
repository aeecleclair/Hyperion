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
from app.core.utils.config import Settings
from app.dependencies import get_settings
from app.types.factory import Factory
from app.types.floors_type import FloorsType

NB_USERS = 100

faker = Faker("fr_FR")
hyperion_error_logger = logging.getLogger("hyperion.error")
try:
    settings: Settings | None = get_settings()
except Exception:
    settings = None
    hyperion_error_logger.warning(
        "Settings not available, using default values for factories. "
        "This is expected if you are running this code outside of the app context. Such as in a test or a script.",
    )


class CoreUsersFactory(Factory):
    demo_users_id = [
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    ]
    demo_nicknames = [
        "Khurzs",
        "Jhobahtes",
        "Thonyk",
        "Schïbah",
        "Askoh",
    ]
    demo_groups = [
        groups_type.GroupType.admin,
        groups_type.GroupType.admin_cdr,
        groups_type.GroupType.BDE,
        groups_type.GroupType.raid_admin,
        groups_type.GroupType.BDS,
    ]
    if settings and settings.USE_FACTORIES and settings.FACTORIES_DEMO_USERS_PASSWORD:
        demo_passwords = [
            security.get_password_hash(settings.FACTORIES_DEMO_USERS_PASSWORD)
            for _ in range(len(demo_users_id))
        ]
    else:
        demo_passwords = [
            security.get_password_hash(faker.password(16, True, True, True, True))
            for _ in range(len(demo_users_id))
        ]

    other_users_id = [str(uuid.uuid4()) for _ in range(NB_USERS)]

    def __init__(self):
        super().__init__(
            depends_on=[],
        )

    async def create_core_users(self, db: AsyncSession):
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
                school_id = SchoolType.centrale_lyon.value
                account_type = groups_type.AccountType.student
            elif i < 3 * NB_USERS // 4:
                email = (firstname[i] + "." + name[i] + "@ec-lyon.fr").lower()
                school_id = SchoolType.centrale_lyon.value
                account_type = groups_type.AccountType.staff
            elif i < 4 * NB_USERS // 5:
                email = (firstname[i] + "." + name[i] + "@centraliens-lyon.net").lower()
                school_id = SchoolType.centrale_lyon.value
                account_type = groups_type.AccountType.former_student
            else:
                email = faker.email()
                school_id = SchoolType.no_school.value
                account_type = groups_type.AccountType.external

            user = CoreUser(
                id=self.other_users_id[i],
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

        for i in range(len(self.demo_users_id)):
            user = CoreUser(
                id=self.demo_users_id[i],
                password_hash=self.demo_passwords[i],
                firstname="Demo " + str(i),
                nickname=self.demo_nicknames[i],
                name="Salut",
                email="demo" + str(i) + "@etu.ec-lyon.fr",
                floor=None,
                phone=None,
                promo=None,
                school_id=SchoolType.centrale_lyon.value,
                account_type=groups_type.AccountType.student,
                birthday=None,
                created_on=datetime.now(tz=UTC),
            )
            await cruds_users.create_user(db=db, user=user)
            await cruds_groups.create_membership(
                db=db,
                membership=CoreMembership(
                    group_id=self.demo_groups[i],
                    user_id=self.demo_users_id[i],
                    description=None,
                ),
            )

    async def run(self, db: AsyncSession):
        await self.create_core_users(db=db)

    async def should_run(self, db: AsyncSession):
        result = len(await cruds_users.get_users(db=db)) == 0
        if not result:
            registered_users = await cruds_users.get_users(db=db)
            self.other_users_id = [
                user.id
                for user in registered_users
                if user.nickname not in self.demo_nicknames
            ]
            self.demo_users_id = [
                user.id
                for user in registered_users
                if user.nickname in self.demo_nicknames
            ]
        return result
