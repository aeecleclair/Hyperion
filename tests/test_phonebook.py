import uuid

from app.dependencies import get_settings
from app.main import app
from app.models import models_core, models_phonebook
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

user: models_core.CoreUser | None = None
CAA_user: models_core.CoreUser | None = None
association: models_phonebook.Association | None = None
role: models_phonebook.Role | None = None
member: models_phonebook.Member | None = None
member2: models_phonebook.Member | None = None

id_asso_1 = str(uuid.uuid4())
id_asso_2 = str(uuid.uuid4())
id_asso_3 = str(uuid.uuid4())

name_asso_1 = "Association1"
name_asso_2 = "Association2"
name_asso_3 = "Association3"

id_role_1 = str(uuid.uuid4())
id_role_2 = str(uuid.uuid4())
name_role_1 = "Role1"
name_role_2 = "Role2"

id_member_1 = str(uuid.uuid4())
id_member_2 = str(uuid.uuid4())
name_member_1 = "Member1"
name_member_2 = "Member2"
first_name_role_1 = "Prénom1"
first_name_role_2 = "Prénom2"
email_member_1 = "mail1"
email_member_2 = "mail2"
nickname_member_1 = "pseudo1"
nickname_member_2 = "pseudo2"


settings = app.dependency_overrides.get(get_settings, get_settings)()


# ---------------------------------- Startup --------------------------------- #
@app.on_event("startup")
async def startuptest():
    global user, association, role, member, CAA_user

    async with TestingSessionLocal() as db:
        user = await create_user_with_groups([GroupType.student], db=db)
        user_2 = await create_user_with_groups([GroupType.student], db=db)

        CAA_user = await create_user_with_groups([GroupType.CAA], db=db)

        global association
        association = models_phonebook.Association(
            id=id_asso_1,
            name=name_asso_1,
        )
        association2 = models_phonebook.Association(
            id=id_asso_2,
            name=name_asso_2,
        )
        association3 = models_phonebook.Association(
            id=id_asso_3,
            name=name_asso_3,
        )

        role = models_phonebook.Role(id=id_role_1, name=name_role_1)
        role2 = models_phonebook.Role(id=id_role_2, name=name_role_2)

        user.name = name_member_1
        user_2.name = name_member_2

        user.firstname = first_name_role_1
        user_2.firstname = first_name_role_2

        user.nickname = nickname_member_1
        user_2.nickname = nickname_member_2

        user.email = email_member_1
        user_2.email = email_member_2

        member = models_phonebook.Member(
            user_id=user.id,
            role_id=role.id,
            mandate_year=2021,
            member_id=id_member_1,
            association_id=id_asso_1,
        )

        member2 = models_phonebook.Member(
            user_id=user_2.id,
            role_id=role2.id,
            mandate_year=2021,
            member_id=id_member_2,
            association_id=id_asso_1,
        )

        db.add(association)
        db.add(association2)
        db.add(association3)
        db.add(role)
        db.add(role2)
        db.add(member)
        db.add(member2)
        await db.commit()


# -------------------------------- Association ------------------------------- #
def test_create_association_by_student():
    token = create_api_access_token(user)

    response = client.post(
        "/phonebook/associations/?name=Fablab",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_create_association_by_CAA():
    token = create_api_access_token(CAA_user)

    response = client.post(
        "/phonebook/associations/?name=Fablab",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_update_association():
    token = create_api_access_token(CAA_user)

    response = client.patch(
        f"/phonebook/associations/{id_asso_2}",
        json={"name": "Usine à Gaz"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_delete_association():
    token = create_api_access_token(CAA_user)

    response = client.delete(
        f"/phonebook/associations/{id_asso_2}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# ---------------------------------- Member ---------------------------------- #
def test_create_member():
    token = create_api_access_token(CAA_user)

    response = client.post(
        f"/phonebook/members/?association_id={id_asso_1}&mandate_year=2022&role_id={id_role_1}&user_id={str(uuid.uuid4())}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_update_member():
    print("-->", id_member_1)
    token = create_api_access_token(CAA_user)

    response = client.patch(
        "/phonebook/members/{id_member_1}",
        json={"role_id": id_role_2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_delete_member():
    token = create_api_access_token(CAA_user)

    response = client.request(
        method="DELETE",
        url=f"/phonebook/members/{id_member_1}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


# ----------------------------------- Role ----------------------------------- #
def test_create_role():
    token = create_api_access_token(CAA_user)

    response = client.post(
        "/phonebook/roles/?role_name=AutreRole",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_update_role():
    token = create_api_access_token(CAA_user)

    response = client.patch(
        "/phonebook/roles/{id_role_1}",
        json={"role_name": "Role1Modifie"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_delete_role():
    token = create_api_access_token(CAA_user)

    response = client.delete(
        "/phonebook/roles/{id_role_2}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# ----------------------------- Association Logo ----------------------------- #
def test_create_association_logo():
    token = create_api_access_token(CAA_user)

    with open("assets/images/default_profile_picture.png", "rb") as image:
        response = client.post(
            f"/phonebook/associations/{id_asso_1}/logo/",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_read_association_logo():
    token = create_api_access_token(user)

    response = client.get(
        f"/phonebook/associations/{id_asso_1}/logo",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


# --------------------------------- Research --------------------------------- #
def test_request_by_person():
    token = create_api_access_token(user)

    response = client.get(
        "/phonebook/research/?query=&query_type=person",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(response.json())
    assert response.status_code == 200


def test_request_by_role():
    token = create_api_access_token(user)

    response = client.get(
        f"/phonebook/research/?query={name_role_1}&query_type=role",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_request_by_association():
    token = create_api_access_token(user)

    response = client.get(
        f"/phonebook/research/?query={name_asso_1}&query_type=association",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
