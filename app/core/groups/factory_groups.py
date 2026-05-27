import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.core.groups.groups_type import GroupType
from app.core.groups.models_groups import CoreGroup, CoreMembership
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.types.factory import Factory


class CoreGroupsFactory(Factory):
    groups_ids = [
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    ]

    depends_on = [CoreUsersFactory]

    @classmethod
    async def create_core_groups(cls, db: AsyncSession):
        groups = ["AEECL", "USEECL", "ECLAIR", "Bazar"]
        descriptions = [
            "Groupe de test",
            "Groupe de test 2",
            "Groupe de prêt",
            "Groupe de prêt 2",
        ]
        for i in range(len(groups)):
            await cruds_groups.create_group(
                db=db,
                group=CoreGroup(
                    id=cls.groups_ids[i],
                    name=groups[i],
                    description=descriptions[i],
                ),
            )

    @classmethod
    async def create_core_memberships(cls, db: AsyncSession):
        for i in range(len(cls.groups_ids)):
            users = random.sample(CoreUsersFactory.other_users_id, 10)

            for user_id in users:
                await cruds_groups.create_membership(
                    db=db,
                    membership=CoreMembership(
                        group_id=cls.groups_ids[i],
                        user_id=user_id,
                        description=None,
                    ),
                )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.create_core_groups(db=db)
        await cls.create_core_memberships(db=db)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_groups.get_groups(db=db)) == len(GroupType)
