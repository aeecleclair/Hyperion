import uuid

from app.core import models_core, security
from app.core.groups import cruds_groups, groups_type
from app.core.users import cruds_users
from app.utils.factory import Factory


async def create_core_users(db):
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

    email = ["demo.test@myecl.fr"] + [
        f"{firstname[i].lower()}.{name[i].lower()}@etu.ec-lyon.fr" for i in range(1, 10)
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

    floor = ["T1", "U1", "U2", "U4", "U56", "U56", "X1", "X2", "X3", "X4"]

    password = "password"

    groups = [[groups_type.GroupType.student] for _ in range(10)]
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
            id=str(uuid.uuid4()),
            password_hash=security.get_password_hash(password),
            firstname=firstname[i],
            nickname=nickname[i],
            name=name[i],
            email=email[i],
            floor=floor[i],
            phone=phone[i],
            promo=promos[i],
        )
        await cruds_users.create_user(db=db, user=user)
        for group in groups[i]:
            await cruds_groups.create_membership(
                db=db,
                membership=models_core.CoreMembership(
                    group_id=group.value,
                    user_id=user.id,
                ),
            )


async def create_core_groups(db):
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


async def should_run(db):
    user = await cruds_users.get_users(db=db)
    if not user:
        return True
    return False


factory = Factory(
    name="core",
    depends_on=[],
    should_run=should_run,
    sub_factories=[create_core_users, create_core_groups],
)
