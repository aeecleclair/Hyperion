import uuid

from app.core.core_endpoints.models_core import CoreGroup
from app.core.factory_core import CoreFactory
from app.core.groups.groups_type import GroupType
from app.core.users import cruds_users
from app.modules.phonebook import cruds_phonebook, models_phonebook
from app.modules.phonebook.types_phonebook import Kinds
from app.types.factory import Factory


class PhonebookFactory(Factory):
    def __init__(self):
        super().__init__(
            name="phonebook",
            depends_on=[CoreFactory],
        )

    async def create_association(self, db):
        association_id_1 = str(uuid.uuid4())
        await cruds_phonebook.create_association(
            association=models_phonebook.Association(
                id=association_id_1,
                name="Eclair",
                description="L'asso d'informatique la plus cool !",
                associated_groups=[
                    CoreGroup(
                        name="Eclair",
                        description="L'asso d'informatique la plus cool !",
                        id=GroupType.eclair,
                        members=[],
                    ),
                ],
                deactivated=False,
                kind=Kinds.section_ae,
                mandate_year=2025,
            ),
            db=db,
        )

        await cruds_phonebook.create_membership(
            membership=models_phonebook.Membership(
                id=str(uuid.uuid4()),
                user_id=CoreFactory.demo_user_id,
                association_id=association_id_1,
                mandate_year=2025,
                role_name="Prez",
                role_tags="Prez",
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
                kind=Kinds.section_ae,
                mandate_year=2025,
            ),
            db=db,
        )

        users = await cruds_users.get_users(db=db)
        for i in range(len(users)):
            user = users[i]
            await cruds_phonebook.create_membership(
                membership=models_phonebook.Membership(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    association_id=association_id_2,
                    mandate_year=2025,
                    role_name=f"VP {user.nickname}",
                    role_tags="Idk",
                    member_order=i,
                ),
                db=db,
            )

    async def run(self, db):
        await self.create_association(db)

    async def should_run(self, db):
        assos = await cruds_phonebook.get_all_associations(db=db)
        return len(assos) == 0


factory = PhonebookFactory()
