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

    def __init__(self):
        super().__init__(
            depends_on=[CoreUsersFactory],
        )

    async def run(self, db: AsyncSession):
        for i in range(len(self.memberships_ids)):
            await cruds_memberships.create_association_membership(
                db,
                MembershipSimple(
                    id=self.memberships_ids[i],
                    name=self.memberships_names[i],
                    manager_group_id=self.memberships_manager_group_id[i],
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
                        association_membership_id=self.memberships_ids[i],
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

    async def should_run(self, db: AsyncSession):
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
            self.memberships_ids = [
                membership.id for membership in registered_memberships
            ]
