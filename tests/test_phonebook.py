import uuid

from app.main import app
from app.models import models_core, models_phonebook
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

global association

membership: models_phonebook.Membership | None = None
association: models_phonebook.Association | None = None
member: models_core.CoreUser | None = None
role: models_phonebook.Role | None = None
phonebook_user_caa: models_core.CoreUser | None = None
phonebook_user_simple: models_core.CoreUser | None = None
token_caa: str = ""
token_simple: str = ""


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global phonebook_user_caa
    async with TestingSessionLocal() as db:
        phonebook_user_caa = await create_user_with_groups([GroupType.CAA], db=db)
        await db.commit()

    global token_caa
    token_caa = create_api_access_token(phonebook_user_caa)

    global phonebook_user_simple
    async with TestingSessionLocal() as db:
        phonebook_user_simple = await create_user_with_groups(
            [GroupType.student], db=db
        )
        await db.commit()

    global token_simple
    token_simple = create_api_access_token(phonebook_user_simple)

    global member
    async with TestingSessionLocal() as db:
        member = models_core.CoreUser(
            id=str(
                uuid.uuid4(),
                name="Jean",
                firstname="Prunte",
                nickname="Duh",
                email="jean.prunte@ecl23.ec-lyon.fr",
            )
        )
        db.add(member)
        await db.commit()

    global role
    async with TestingSessionLocal() as db:
        role = models_phonebook.Role(id=str(uuid.uuid4()), name="VP Emprunts")
        db.add(role)
        await db.commit()

    global association
    async with TestingSessionLocal() as db:
        association = models_phonebook.Association(
            id=str(uuid.uuid4()), type="Section", name="ECLAIR"
        )
        db.add(association)
        await db.commit()

    global membership
    async with TestingSessionLocal() as db:
        membership = models_phonebook.Membership(
            user_id=member.id, association_id=association.id, role_id=role.id
        )
        db.add(membership)
        await db.commit()


def test_get_all_associations_admin():
    response = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 200


def test_get_all_associations_simple():
    response = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_association_admin():
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201


def test_create_association_simple():
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_add_membership_admin():
    # create a new association to join
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "phonebook/associations/membership",
        json={
            "user_id": member.id,
            "association_id": association_id,
            "role_id": role.id,
        },
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201


def test_add_membership_simple():
    # create a new association to join
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "phonebook/associations/membership",
        json={
            "user_id": member.id,
            "association_id": association_id,
            "role_id": role.id,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_membership_admin():
    # create a membership to delete
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "phonebook/associations/membership",
        json={
            "user_id": member.id,
            "association_id": association_id,
            "role_id": role.id,
        },
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    member_id = response.json()["user_id"]

    response = client.delete(
        "/phonebook/associations/membership",
        json={"association_id": association_id, "user_id": member_id},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 204


def test_delete_membership_simple():
    # create a membership to delete
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "phonebook/associations/membership",
        json={
            "user_id": member.id,
            "association_id": association_id,
            "role_id": role.id,
        },
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    member_id = response.json()["user_id"]

    response = client.delete(
        "/phonebook/associations/membership",
        json={"association_id": association_id, "user_id": member_id},
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_update_association_admin():
    response = client.patch(
        f"/phonebook/associations/{association.id}/",
        json={"name": "Éclair"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 204


def test_update_association_simple():
    response = client.patch(
        f"/phonebook/associations/{association.id}/",
        json={"name": "Éclair"},
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_association_admin():
    # create an association to delete
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Piston Hebdo", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.delete(
        f"/phonebook/associations/{association_id}/",
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 204


def test_delete_association_simple():
    # create an association to delete
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Piston Hebdo", "type": "Gros Club"},
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.delete(
        f"/phonebook/associations/{association_id}/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_members_by_association_id_admin():
    response = client.get(
        f"/phonebook/associations/{association.id}/members/",
        headers={"Authorization": f"Bearer {token_caa}"},
    )
    assert response.status_code == 200


def test_get_members_by_association_id_simple():
    response = client.get(
        f"/phonebook/associations/{association.id}/members/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
