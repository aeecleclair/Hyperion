import datetime
import random
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.memberships import cruds_memberships
from app.core.memberships.schemas_memberships import (
    MembershipSimple,
    UserMembershipSimple,
)
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.types.factory import Factory


class CoreMembershipsFactory(Factory):
    memberships_ids = [
        uuid4(),
        uuid4(),
    ]
    memberships_names = [
        "AEECL",
        "USEECL",
    ]
    memberships_manager_group_id = [
        GroupType.BDE.value,
        GroupType.BDS.value,
    ]

    depends_on = [CoreUsersFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        for i in range(len(cls.memberships_ids)):
            await cruds_memberships.create_association_membership(
                db,
                MembershipSimple(
                    id=cls.memberships_ids[i],
                    name=cls.memberships_names[i],
                    manager_group_id=cls.memberships_manager_group_id[i],
                ),
            )

            members = random.sample(
                CoreUsersFactory.other_users_id,
                20,
            )
            for user_id in members:
                await cruds_memberships.create_user_membership(
                    db=db,
                    user_membership=UserMembershipSimple(
                        id=uuid4(),
                        user_id=user_id,
                        association_membership_id=cls.memberships_ids[i],
                        start_date=datetime.datetime(
                            random.randint(2020, 2023),  # noqa: S311
                            random.randint(1, 12),  # noqa: S311
                            random.randint(1, 28),  # noqa: S311
                            tzinfo=datetime.UTC,
                        ),
                        end_date=datetime.datetime(
                            random.randint(2025, 2027),  # noqa: S311
                            random.randint(1, 12),  # noqa: S311
                            random.randint(1, 28),  # noqa: S311
                            tzinfo=datetime.UTC,
                        ),
                    ),
                )
        await db.commit()

    @classmethod
    async def should_run(cls, db: AsyncSession):
        result = (
            len(
                await cruds_memberships.get_association_memberships(
                    db=db,
                ),
            )
            == 0
        )
        if not result:
            registered_memberships = (
                await cruds_memberships.get_association_memberships(
                    db=db,
                )
            )
            cls.memberships_ids = [
                membership.id for membership in registered_memberships
            ]
