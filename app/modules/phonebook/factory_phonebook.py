import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import cruds_users
from app.core.users.factory_users import CoreUsersFactory
from app.modules.phonebook import cruds_phonebook, models_phonebook
from app.modules.phonebook.types_phonebook import Kinds, RoleTags
from app.types.factory import Factory


class PhonebookFactory(Factory):
    def __init__(self):
        super().__init__(
            depends_on=[CoreUsersFactory],
        )

    async def create_association(self, db: AsyncSession):
        association_id_1 = str(uuid.uuid4())
        await cruds_phonebook.create_association(
            association=models_phonebook.Association(
                id=association_id_1,
                name="Eclair",
                description="L'asso d'informatique la plus cool !",
                deactivated=False,
                kind=Kinds.section_ae,
                mandate_year=2025,
            ),
            db=db,
        )

        await cruds_phonebook.create_membership(
            membership=models_phonebook.Membership(
                id=str(uuid.uuid4()),
                user_id=CoreUsersFactory.demo_users_id[0],
                association_id=association_id_1,
                mandate_year=2025,
                role_name="Prez",
                role_tags=RoleTags.president.name,
                member_order=1,
            ),
            db=db,
        )

        association_id_2 = str(uuid.uuid4())
        await cruds_phonebook.create_association(
            association=models_phonebook.Association(
                id=association_id_2,
                name="Association 2",
                description="Description de l'asso 2",
                associated_groups=[],
                deactivated=False,
                kind=Kinds.section_use,
                mandate_year=2025,
            ),
            db=db,
        )
        users = await cruds_users.get_users(db=db)
        tags = list(RoleTags)
        for i, user in enumerate(random.sample(users, 10)):
            await cruds_phonebook.create_membership(
                membership=models_phonebook.Membership(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    association_id=association_id_2,
                    mandate_year=2025,
                    role_name=f"VP {i}",
                    role_tags=tags[i].name if i < len(tags) else "",
                    member_order=i,
                ),
                db=db,
            )

    async def run(self, db: AsyncSession):
        await self.create_association(db)

    async def should_run(self, db: AsyncSession):
        assos = await cruds_phonebook.get_all_associations(db=db)
        return len(assos) == 0
