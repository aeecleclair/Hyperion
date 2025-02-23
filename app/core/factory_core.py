import uuid
from datetime import UTC, datetime

from app.core import models_core, security
from app.core.groups import cruds_groups, groups_type
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users
from app.types.floors_type import FloorsType
from app.utils.factory import Factory


class CoreFactory(Factory):
    demo_user_id = str(uuid.uuid4())
    def __init__(self):
        super().__init__(
            name="core",
            depends_on=[],
        )

    async def create_core_users(self, db):
        firstname = [
            "demo",
            "Jean",
            "Paul",
            "Jacques",
            "Pierre",
            "Marie",
            "Anne",
            "Sophie",
            "Lucie",
            "Julie",
        ]
        name = [
            "test",
            "Dupont",
            "Durand",
            "Martin",
            "Bernard",
            "Dubois",
            "Thomas",
            "Robert",
            "Richard",
            "Petit",
        ]

        email = ["demo.test@etu.ec-lyon.fr"] + [
            f"{firstname[i].lower()}.{name[i].lower()}@etu.ec-lyon.fr"
            for i in range(1, 10)
        ]

        nickname = [
            "ÉCLAIR",
            "Jaja",
            "Polo",
            "Jacky",
            "Pierrot",
            "Mamie",
            None,
            "Soph",
            None,
            "Juju",
        ]

        password = "password"

        groups: list[list[groups_type.GroupType]] = [[], [], [], []]
        groups[0].append(groups_type.GroupType.admin)
        groups[1].append(groups_type.GroupType.amap)
        groups[2].append(groups_type.GroupType.BDE)
        groups[3].append(groups_type.GroupType.CAA)

        phone = [
            "0610203040",
            "0611213141",
            "0621223242",
            "0632233343",
            "0643243444",
            "0654253545",
            "0665263646",
            "0676273747",
            "0687283848",
            "0698293949",
        ]

        promos = [2019, 2019, 2020, 2020, 2021, 2021, 2022, 2022, 2023, 2023]

        for i in range(10):
            user = models_core.CoreUser(
                id=str(uuid.uuid4()) if i != 0 else self.demo_user_id,
                password_hash=security.get_password_hash(password),
                firstname=firstname[i],
                nickname=nickname[i],
                name=name[i],
                email=email[i],
                floor=FloorsType.Adoma,
                phone=phone[i],
                promo=promos[i],
                school_id=SchoolType.no_school.value,
                account_type=groups_type.AccountType.student,
                birthday=None,
                created_on=datetime.now(tz=UTC),
            )
            await cruds_users.create_user(db=db, user=user)
            for group in groups[i%4]:
                await cruds_groups.create_membership(
                    db=db,
                    membership=models_core.CoreMembership(
                        group_id=group.value,
                        user_id=user.id,
                        description="Groupe de test",
                    ),
                )

    async def create_core_groups(self, db):
        groups = ["ÉCLAIR", "Pixels"]
        descriptions = ["Groupe de test", "Groupe de test 2"]
        for i in range(len(groups)):
            await cruds_groups.create_group(
                db=db,
                group=models_core.CoreGroup(
                    id=str(uuid.uuid4()),
                    name=groups[i],
                    description=descriptions[i],
                ),
            )

    async def run(self, db):
        await self.create_core_users(db)
        await self.create_core_groups(db)

    async def should_run(self, db):
        user = await cruds_users.get_users(db=db)
        return len(user) == 0


factory = CoreFactory()
