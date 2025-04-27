import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.core.groups.groups_type import GroupType
from app.core.groups.models_groups import CoreGroup, CoreMembership
from app.core.users.factory_users import CoreUsersFactory
from app.types.factory import Factory


class CoreGroupsFactory(Factory):
    groups_ids = [
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    ]

    def __init__(self):
        super().__init__(
            depends_on=[CoreUsersFactory],
        )

    async def create_core_groups(self, db: AsyncSession):
        groups = ["Oui", "Pixels"]
        descriptions = ["Groupe de test", "Groupe de test 2"]
        for i in range(len(groups)):
            await cruds_groups.create_group(
                db=db,
                group=CoreGroup(
                    id=self.groups_ids[i],
                    name=groups[i],
                    description=descriptions[i],
                ),
            )

    async def create_core_memberships(self, db: AsyncSession):
        for i in range(len(self.groups_ids)):
            users = random.sample(CoreUsersFactory.other_users_id, 10)

            for user_id in users:
                await cruds_groups.create_membership(
                    db=db,
                    membership=CoreMembership(
                        group_id=self.groups_ids[i],
                        user_id=user_id,
                        description=None,
                    ),
                )

    async def run(self, db: AsyncSession):
        await self.create_core_groups(db=db)
        await self.create_core_memberships(db=db)

    async def should_run(self, db: AsyncSession):
        return len(await cruds_groups.get_groups(db=db)) == len(GroupType)
