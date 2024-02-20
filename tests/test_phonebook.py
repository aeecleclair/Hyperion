import uuid

import pytest_asyncio

from app.models import models_core, models_phonebook
from app.schemas import schemas_phonebook
from app.utils.types.groups_type import GroupType
from tests.commons import event_loop  # noqa
from tests.commons import (
    add_object_to_db,
    change_redis_client_status,
    client,
    create_api_access_token,
    create_user_with_groups,
)

membership: models_phonebook.Membership | None = None
association: models_phonebook.Association | None = None
# role: models_phonebook.Role | None = None
phonebook_user_BDE: models_core.CoreUser | None = None
phonebook_user_simple: models_core.CoreUser | None = None
token_BDE: str = ""
token_simple: str = ""
membership_id: str = str(uuid.uuid4())


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global phonebook_user_BDE
    phonebook_user_BDE = await create_user_with_groups([GroupType.BDE], db=db)

    global token_BDE
    token_BDE = create_api_access_token(phonebook_user_BDE)

    global phonebook_user_simple
    phonebook_user_simple = await create_user_with_groups(
            [GroupType.student], db=db
        )
        


    global token_simple
    token_simple = create_api_access_token(phonebook_user_simple)

    # global role
    # async with TestingSessionLocal() as db:
    #     role = models_phonebook.Role(id=str(uuid.uuid4()), name="VP Emprunts")
    #     db.add(role)
    #     await db.commit()

    global association
   
    association = models_phonebook.Association(
            id=str(uuid.uuid4()), kind="Section", name="ECLAIR", mandate_year=2023
        )

    await add_object_to_db(association)
    global membership

    membership = models_phonebook.Membership(
            id=membership_id,
            user_id=phonebook_user_simple.id,
            association_id=association.id,
            # role_id=role.id,
            role_tags="VP Emprunts",
            role_name="VP Emprunts",
            mandate_year=2023,
        )
    await add_object_to_db(membership)




# ---------------------------------------------------------------------------- #
#                              Associations tests                              #
# ---------------------------------------------------------------------------- #
def test_get_all_associations_admin():
    response = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 200


def test_get_all_associations_simple():
    response = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_association_admin():
    print("----------->", token_BDE)
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Gros Club",
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201


def test_create_association_simple():

    response = client.post(
        '/phonebook/associations/',
        json={
            "name": "Bazar",
            "kind": "Gros Club",
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},)
    id = response.json()["id"]
    response = client.post(
        "/phonebook/associations/",
        json={
            "id": id,
            "name": "Bazar",
            "kind": "Gros Club",
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_update_association_admin():
    response = client.post(
        '/phonebook/associations/',
        json={
            "name": "Bazar",
            "kind": "Gros Club",
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},)
    id = response.json()["id"]

    response = client.patch(
        f"/phonebook/associations/{id}",
        json={
            "id": id,
            "name": "Bazar",
            "kind": "Gros Club",
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
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
        json={
            "name": "Piston Hebdo",
            "kind": "Gros Club",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.delete(
        f"/phonebook/associations/{association_id}/",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_delete_association_simple():
    # create an association to delete
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Piston Hebdo",
            "kind": "Gros Club",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.delete(
        f"/phonebook/associations/{association_id}/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_all_association_kinds_admin():
    response = client.get(
        "/phonebook/associations/kinds",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 200


def test_get_all_association_kinds_simple():
    response = client.get(
        "/phonebook/associations/kinds",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------- #
#                               Memberships tests                              #
# ---------------------------------------------------------------------------- #
def test_add_membership_admin():
    # create a new association to join
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Gros Club",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association_id,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",

        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_add_membership_simple():
    # create a new association to join
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Gros Club",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association_id,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_update_membership_admin():
    # create a new association to join
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Gros Club",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association_id,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204
    membership_id = response.json()["id"]

    response = client.patch(
        f"/phonebook/associations/memberships/{membership_id}", json={"role_name": "Autre rôle"},
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_delete_membership_admin():
    # create a membership to delete
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Gros Club",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association_id,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    membership_id = response.json()["id"]
    print("+++>", membership_id, type(membership_id))

    response = client.request(
        method="DELETE",
        url=f"/phonebook/associations/memberships/{membership_id}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_delete_membership_simple():
    # create a membership to delete
    response = client.post(
        "/phonebook/associations/",
        json={"name": "Bazar", "kind": "Gros Club", "mandate_year": 2023},
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201
    association_id = response.json()["id"]

    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association_id,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204
    membership_id = response.json()["id"]
    membership_mandate_year = response.json()["mandate_year"]

    response = client.request(
        method="DELETE",
        url=f"/phonebook/associations/memberships/{membership_mandate_year}",
        json={"membership_id": membership_id},
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403



# ---------------------------------------------------------------------------- #
#                                  Get X by Y                                  #
# ---------------------------------------------------------------------------- #


def test_get_members_by_association_id_admin():
    response = client.get(
        f"/phonebook/associations/{association.id}/members/{association.mandate_year}",
        headers={"Authorization": f"Bearer {token_BDE}"
                 },
    )
    assert response.status_code == 200
    assert isinstance(response.json(),list)
    for k in response.json():
        assert isinstance(response.json()[k], schemas_phonebook.MemberComplete)



def test_get_members_by_association_id_simple():
    response = client.get(
        f"/phonebook/associations/{association.id}/members/{association.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(),list)
    for k in response.json():
        assert isinstance(response.json()[k], schemas_phonebook.MemberComplete)


def test_get_member_by_id_admin():
    response = client.get(
        f"phonebook/member/{phonebook_user_simple.id}",
        headers={"Authorization": f"Bearer {token_BDE}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), schemas_phonebook.MemberBase)

def test_get_member_by_id_simple():
    response = client.get(
        f"phonebook/member/{phonebook_user_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), schemas_phonebook.MemberBase)

def test_get_member_complete_by_id_admin():
    response = client.get(
        f"phonebook/member/{phonebook_user_simple.id}/complete",
        headers={"Authorization": f"Bearer {token_BDE}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), schemas_phonebook.MemberComplete)

def test_get_member_complete_by_id_simple():
    response = client.get(
        f"phonebook/member/{phonebook_user_simple.id}/complete",
        headers={"Authorization": f"Bearer {token_simple}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), schemas_phonebook.MemberComplete)


# ---------------------------------------------------------------------------- #
#                                Roletags tests                                #
# ---------------------------------------------------------------------------- #
def test_get_all_roletags_admin():
    response = client.get(
        "/phonebook/roletags/", headers={"Authorization": f"Bearer {token_BDE}"}
    )
    assert response.status_code == 200


def test_get_all_roletags_simple():
    response = client.get(
        "/phonebook/roletags/", headers={"Authorization": f"Bearer {token_simple}"}
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                                  Logos tests                                 #
# ---------------------------------------------------------------------------- #
def test_create_association_picture_admin():
    with open("assets/images/default_association_picture.png", "rb") as image:
        response = client.post(
            f"/phonebook/associations/{association.id}/picture",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_BDE}"},
        )

    assert response.status_code == 201


def test_create_association_picture_simple():
    with open("assets/images/default_association_picture.png", "rb") as image:
        response = client.post(
            f"/phonebook/associations/{association.id}/picture",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_simple}"},
        )

    assert response.status_code == 403


def test_get_association_picture_admin():
    response = client.get(
        f"/phonebook/associations/{association.id}/picture",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )

    assert response.status_code == 200


def test_get_association_picture_simple():
    response = client.get(
        f"/phonebook/associations/{association.id}/picture",
        headers={"Authorization": f"Bearer {token_simple}"},
    )

    assert response.status_code == 200
