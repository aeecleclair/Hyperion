import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.associations import cruds_associations
from app.core.associations.models_associations import CoreAssociation
from app.core.groups.factory_groups import CoreGroupsFactory
from app.core.utils.config import Settings
from app.types.factory import Factory


class AssociationsFactory(Factory):
    association_ids = [
        uuid.uuid4(),
        uuid.uuid4(),
    ]

    depends_on = [CoreGroupsFactory]

    @classmethod
    async def create_associations(cls, db: AsyncSession):
        descriptions = ["Association 1", "Association 2"]
        for i in range(len(CoreGroupsFactory.groups_ids)):
            await cruds_associations.create_association(
                db=db,
                association=CoreAssociation(
                    id=cls.association_ids[i],
                    name=descriptions[i],
                    group_id=CoreGroupsFactory.groups_ids[i],
                ),
            )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.create_associations(db=db)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_associations.get_associations(db=db)) > 0
