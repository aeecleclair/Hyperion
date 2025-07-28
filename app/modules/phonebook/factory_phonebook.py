import random
import uuid

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import cruds_users
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.phonebook import cruds_phonebook, schemas_phonebook
from app.modules.phonebook.types_phonebook import RoleTags
from app.types.factory import Factory

faker = Faker("fr_FR")


class PhonebookFactory(Factory):
    depends_on = [CoreUsersFactory]

    @classmethod
    async def create_association_groupement(cls, db: AsyncSession) -> list[uuid.UUID]:
        groupement_ids = [uuid.uuid4() for _ in range(3)]
        await cruds_phonebook.create_groupement(
            schemas_phonebook.AssociationGroupement(
                id=groupement_ids[0],
                name="Section AE",
            ),
            db=db,
        )
        await cruds_phonebook.create_groupement(
            schemas_phonebook.AssociationGroupement(
                id=groupement_ids[1],
                name="Club AE",
            ),
            db=db,
        )
        await cruds_phonebook.create_groupement(
            schemas_phonebook.AssociationGroupement(
                id=groupement_ids[2],
                name="Section USE",
            ),
            db=db,
        )
        return groupement_ids

    @classmethod
    async def create_association(
        cls,
        db: AsyncSession,
        groupement_ids: list[uuid.UUID],
    ):
        for i in range(5):
            association_id = str(uuid.uuid4())
            await cruds_phonebook.create_association(
                association=schemas_phonebook.AssociationComplete(
                    id=association_id,
                    groupement_id=groupement_ids[i % len(groupement_ids)],
                    name=faker.company(),
                    description="Description de l'association",
                    associated_groups=[],
                    deactivated=False,
                    mandate_year=2025,
                ),
                db=db,
            )
            users = await cruds_users.get_users(db=db)
            tags = list(RoleTags)
            for j, user in enumerate(random.sample(users, 10)):
                await cruds_phonebook.create_membership(
                    membership=schemas_phonebook.MembershipComplete(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        association_id=association_id,
                        mandate_year=2025,
                        role_name=f"VP {j}",
                        role_tags=tags[j].name if j < len(tags) else "",
                        member_order=j,
                    ),
                    db=db,
                )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        groupement_ids = await cls.create_association_groupement(db=db)
        await cls.create_association(db, groupement_ids=groupement_ids)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        assos = await cruds_phonebook.get_all_associations(db=db)
        return len(assos) == 0
