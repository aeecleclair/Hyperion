import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.phonebook import models_phonebook
from app.modules.phonebook.types_phonebook import Kinds, RoleTags
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

association1: models_phonebook.Association
association2: models_phonebook.Association
association3: models_phonebook.Association

membership1: models_phonebook.Membership
membership2: models_phonebook.Membership
membership3: models_phonebook.Membership
membership4: models_phonebook.Membership
membership5: models_phonebook.Membership
membership6: models_phonebook.Membership
phonebook_user_BDE: models_core.CoreUser
phonebook_user_president: models_core.CoreUser
phonebook_user_simple: models_core.CoreUser
phonebook_user_simple2: models_core.CoreUser
phonebook_user_simple3: models_core.CoreUser

token_BDE: str = ""
token_president: str = ""
token_simple: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global phonebook_user_BDE
    global token_BDE
    global phonebook_user_president
    global token_president
    global phonebook_user_simple
    global phonebook_user_simple2
    global phonebook_user_simple3
    global token_simple

    global association1
    global association2
    global association3

    global membership1
    global membership2
    global membership3
    global membership4
    global membership5
    global membership6

    phonebook_user_BDE = await create_user_with_groups(
        [GroupType.student, GroupType.BDE],
    )
    token_BDE = create_api_access_token(phonebook_user_BDE)

    phonebook_user_president = await create_user_with_groups([GroupType.student])
    token_president = create_api_access_token(phonebook_user_president)

    phonebook_user_simple = await create_user_with_groups([GroupType.student])
    token_simple = create_api_access_token(phonebook_user_simple)

    phonebook_user_simple2 = await create_user_with_groups([GroupType.student])
    phonebook_user_simple3 = await create_user_with_groups([GroupType.student])

    association1 = models_phonebook.Association(
        id="1",
        kind=Kinds.section_ae,
        name="ECLAIR",
        mandate_year=2023,
    )

    association2 = models_phonebook.Association(
        id="2",
        kind=Kinds.association_independant,
        name="Nom",
        mandate_year=2023,
    )

    association3 = models_phonebook.Association(
        id="3",
        kind=Kinds.club_ae,
        name="Test prez",
        mandate_year=2023,
    )

    membership1 = models_phonebook.Membership(
        id="1",
        user_id=phonebook_user_president.id,
        association_id=association1.id,
        role_tags=RoleTags.president.value,
        role_name="Prez",
        mandate_year=association1.mandate_year,
        order=0,
    )

    membership2 = models_phonebook.Membership(
        id="2",
        user_id=phonebook_user_BDE.id,
        association_id=association1.id,
        role_tags="",
        role_name="VP",
        mandate_year=association1.mandate_year,
        order=1,
    )

    membership3 = models_phonebook.Membership(
        id="3",
        user_id=phonebook_user_simple.id,
        association_id=association1.id,
        role_tags="",
        role_name="VP",
        mandate_year=association1.mandate_year,
        order=2,
    )

    membership4 = models_phonebook.Membership(
        id="4",
        user_id=phonebook_user_simple2.id,
        association_id=association1.id,
        role_tags="",
        role_name="VP",
        mandate_year=association1.mandate_year,
        order=3,
    )

    membership5 = models_phonebook.Membership(
        id="5",
        user_id=phonebook_user_simple.id,
        association_id=association2.id,
        role_tags="",
        role_name="VP",
        mandate_year=association2.mandate_year,
        order=0,
    )

    membership6 = models_phonebook.Membership(
        id="6",
        user_id=phonebook_user_president.id,
        association_id=association1.id,
        role_tags="",
        role_name="VP",
        mandate_year=association1.mandate_year - 1,
        order=0,
    )

    await add_object_to_db(association1)
    await add_object_to_db(association2)
    await add_object_to_db(association3)

    await add_object_to_db(membership1)
    await add_object_to_db(membership2)
    await add_object_to_db(membership3)
    await add_object_to_db(membership4)
    await add_object_to_db(membership5)
    await add_object_to_db(membership6)


# ---------------------------------------------------------------------------- #
#                              Get tests                                       #
# ---------------------------------------------------------------------------- #
def test_get_all_associations():
    response = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_all_association_kinds_simple():
    response = client.get(
        "/phonebook/associations/kinds",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.json()["kinds"] == [kind.value for kind in Kinds]


def test_get_all_roletags_simple():
    response = client.get(
        "/phonebook/roletags/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.json()["tags"] == [tag.value for tag in RoleTags]


def test_get_members_by_association_id_simple():
    response = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 4

    assert any(
        member["id"] == phonebook_user_president.id for member in response.json()
    )
    assert any(member["id"] == phonebook_user_BDE.id for member in response.json())
    assert any(member["id"] == phonebook_user_simple.id for member in response.json())
    assert any(member["id"] == phonebook_user_simple2.id for member in response.json())


def test_get_member_by_id_simple():
    response = client.get(
        f"phonebook/member/{phonebook_user_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    member = response.json()
    assert member["id"] == phonebook_user_simple.id
    assert member["email"] == phonebook_user_simple.email
    assert member["name"] == phonebook_user_simple.name
    assert member["firstname"] == phonebook_user_simple.firstname
    assert len(member["memberships"]) == 2


# ---------------------------------------------------------------------------- #
#                              Post tests                                      #
# ---------------------------------------------------------------------------- #


def test_create_association_simple():
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Section USE",
            "mandate_year": 2023,
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    association = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()
    assert len(association) == 3


def test_create_association_admin():
    response = client.post(
        "/phonebook/associations/",
        json={
            "name": "Bazar",
            "kind": "Section USE",
            "mandate_year": 2023,
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )

    association = response.json()

    assert response.status_code == 201
    assert association["name"] == "Bazar"
    assert association["kind"] == "Section USE"
    assert association["mandate_year"] == 2023
    assert association["description"] == "Bazar description"
    assert isinstance(association["id"], str)


def test_add_membership_simple():
    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple2.id,
            "association_id": association2.id,
            "mandate_year": 2023,
            "role_name": "VP Emprunts",
            "role_tags": "",
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    members = client.get(
        f"/phonebook/associations/{association2.id}/members/{association2.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(members) == 1


def test_add_membership_admin():
    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple2.id,
            "association_id": association2.id,
            "mandate_year": 2023,
            "role_name": "VP Emprunts",
            "role_tags": "",
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201

    response_membership = response.json()
    members = client.get(
        f"/phonebook/associations/{association2.id}/members/{association2.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(members) == 2
    assert response_membership["user_id"] == phonebook_user_simple2.id
    assert response_membership["association_id"] == association2.id
    assert response_membership["role_name"] == "VP Emprunts"
    assert response_membership["role_tags"] == ""
    assert response_membership["order"] == 1

    assert any(response_membership in member["memberships"] for member in members)


def test_add_membership_president_with_president_tag():
    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple3.id,
            "association_id": association3.id,
            "mandate_year": association3.mandate_year,
            "role_name": "Prez",
            "role_tags": RoleTags.president.value,
            "order": 0,
        },
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 403

    members = client.get(
        f"/phonebook/associations/{association3.id}/members/{association3.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(members) == 0


def test_add_membership_admin_with_president_tag():
    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple3.id,
            "association_id": association3.id,
            "mandate_year": association3.mandate_year,
            "role_name": "Prez",
            "role_tags": RoleTags.president.value,
            "order": 0,
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201

    members = client.get(
        f"/phonebook/associations/{association3.id}/members/{association3.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(members) == 1

    user_simple3 = members[0]

    assert user_simple3["id"] == phonebook_user_simple3.id
    assert user_simple3["name"] == phonebook_user_simple3.name
    assert user_simple3["firstname"] == phonebook_user_simple3.firstname
    assert user_simple3["email"] == phonebook_user_simple3.email
    assert len(user_simple3["memberships"]) == 1
    assert user_simple3["memberships"][0]["association_id"] == association3.id
    assert user_simple3["memberships"][0]["role_name"] == "Prez"
    assert user_simple3["memberships"][0]["role_tags"] == RoleTags.president.value
    assert user_simple3["memberships"][0]["order"] == 0


# ---------------------------------------------------------------------------- #
#                              Update tests                                    #
# ---------------------------------------------------------------------------- #
def test_update_association_simple():
    response = client.patch(
        f"/phonebook/associations/{association1.id}/",
        json={
            "name": "Éclair",
            "description": "Foudroyante",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    associations = client.get(
        "/phonebook/associations",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()
    association = next(
        (
            association
            for association in associations
            if association["id"] == association1.id
        ),
        None,
    )
    assert association is not None
    assert association["name"] == "ECLAIR"
    assert association["mandate_year"] == 2023


def test_update_association_admin():
    response = client.patch(
        f"/phonebook/associations/{association2.id}",
        json={
            "name": "Bazar",
            "description": "Bazar description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    associations = client.get(
        "/phonebook/associations",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()
    association = next(
        (
            association
            for association in associations
            if association["id"] == association2.id
        ),
        None,
    )

    assert association is not None
    assert association["name"] == "Bazar"
    assert association["description"] == "Bazar description"


def test_update_association_president():
    response = client.patch(
        f"/phonebook/associations/{association1.id}",
        json={
            "name": "eclair",
            "description": "en minuscule",
        },
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 204

    associations = client.get(
        "/phonebook/associations",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()
    association = next(
        (
            association
            for association in associations
            if association["id"] == association1.id
        ),
        None,
    )

    assert association is not None
    assert association["name"] == "eclair"
    assert association["description"] == "en minuscule"


def test_update_membership_simple():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership1.id}",
        json={
            "role_name": "Un rôle",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    user_president = next(
        (member for member in members if member["id"] == phonebook_user_president.id),
        None,
    )

    assert user_president is not None

    membership = next(
        (
            membership
            for membership in user_president["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == association1.mandate_year
        ),
        None,
    )

    assert membership is not None
    assert membership["role_name"] == "Prez"


def test_update_membership_admin():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership1.id}",
        json={
            "role_name": "Autre rôle",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    user_president = next(
        (member for member in members if member["id"] == phonebook_user_president.id),
        None,
    )

    assert user_president is not None

    membership = next(
        (
            membership
            for membership in user_president["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == association1.mandate_year
        ),
        None,
    )

    assert membership is not None
    assert membership["role_name"] == "Autre rôle"


def test_update_membership_president():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership1.id}",
        json={
            "role_name": "Un super rôle",
        },
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    user_president = next(
        (member for member in members if member["id"] == phonebook_user_president.id),
        None,
    )
    assert user_president is not None

    membership = next(
        (
            membership
            for membership in user_president["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == association1.mandate_year
        ),
        None,
    )

    assert membership is not None
    assert membership["role_name"] == "Un super rôle"


def test_update_membership_president_with_president_tag():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership2.id}",
        json={
            "role_tags": RoleTags.president.value,
        },
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 403

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    user_BDE = next(
        (member for member in members if member["id"] == phonebook_user_BDE.id),
        None,
    )

    assert user_BDE is not None

    membership = next(
        (
            membership
            for membership in user_BDE["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == association1.mandate_year
        ),
        None,
    )

    assert membership is not None
    assert membership["role_tags"] == ""


def test_update_membership_admin_with_president_tag():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership2.id}",
        json={
            "role_tags": RoleTags.president.value,
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    user_BDE = next(
        (member for member in members if member["id"] == phonebook_user_BDE.id),
        None,
    )

    assert user_BDE is not None

    membership = next(
        (
            membership
            for membership in user_BDE["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == association1.mandate_year
        ),
        None,
    )

    assert membership is not None
    assert membership["role_tags"] == RoleTags.president.value


def test_update_membership_order():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership1.id}",
        json={
            "order": 2,
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    user_president = next(
        (member for member in members if member["id"] == phonebook_user_president.id),
        None,
    )
    user_BDE = next(
        (member for member in members if member["id"] == phonebook_user_BDE.id),
        None,
    )
    user_simple = next(
        (member for member in members if member["id"] == phonebook_user_simple.id),
        None,
    )

    user_simple2 = next(
        (member for member in members if member["id"] == phonebook_user_simple2.id),
        None,
    )

    assert user_president is not None
    assert user_BDE is not None
    assert user_simple is not None
    assert user_simple2 is not None

    membership_president = next(
        (
            membership
            for membership in user_president["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == 2023
        ),
        None,
    )

    assert membership_president is not None
    assert membership_president["order"] == 2

    membership_president2 = next(
        (
            membership
            for membership in user_president["memberships"]
            if membership["association_id"] == association1.id
            and membership["mandate_year"] == 2022
        ),
        None,
    )

    assert membership_president2 is not None
    assert membership_president2["order"] == 0

    membership_BDE = next(
        (
            membership
            for membership in user_BDE["memberships"]
            if membership["association_id"] == association1.id
        ),
        None,
    )

    assert membership_BDE is not None
    assert membership_BDE["order"] == 0

    membership_simple = next(
        (
            membership
            for membership in user_simple["memberships"]
            if membership["association_id"] == association1.id
        ),
        None,
    )

    assert membership_simple is not None
    assert membership_simple["order"] == 1

    membership_simple2 = next(
        (
            membership
            for membership in user_simple2["memberships"]
            if membership["association_id"] == association2.id
        ),
        None,
    )

    assert membership_simple2 is not None
    assert membership_simple2["order"] == 1


# ---------------------------------------------------------------------------- #
#                              Delete tests                                    #
# ---------------------------------------------------------------------------- #


def test_delete_membership_simple():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership6.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year - 1}",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(members) == 1


def test_delete_membership_admin():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership4.id}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    ).json()

    assert len(members) == 3


def test_delete_membership_president():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership3.id}",
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_president}"},
    ).json()

    assert len(members) == 2


def test_delete_membership_update_order():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership1.id}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    members = client.get(
        f"/phonebook/associations/{association1.id}/members/{association1.mandate_year}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    ).json()

    user_BDE = next(
        (member for member in members if member["id"] == phonebook_user_BDE.id),
        None,
    )

    assert user_BDE is not None

    membership = next(
        (
            membership
            for membership in user_BDE["memberships"]
            if membership["association_id"] == association1.id
        ),
        None,
    )

    assert membership is not None
    assert membership["order"] == 0


def test_delete_association_simple():
    response = client.delete(
        f"/phonebook/associations/{association1.id}/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    associations = client.get(
        "/phonebook/associations",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()
    association = next(
        (
            association
            for association in associations
            if association["id"] == association1.id
        ),
        None,
    )
    assert association is not None
    assert association["name"] == "eclair"
    assert association["description"] == "en minuscule"


def test_delete_association_admin():
    response = client.delete(
        f"/phonebook/associations/{association2.id}/",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204

    associations = client.get(
        "/phonebook/associations",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()
    association = next(
        (
            association
            for association in associations
            if association["id"] == association2.id
        ),
        None,
    )
    assert association is None


# # ---------------------------------------------------------------------------- #
# #                                  Logos tests                                 #
# # ---------------------------------------------------------------------------- #
# def test_create_association_picture_admin():
#     with Path.open("assets/images/default_association_picture.png", "rb") as image:
#         response = client.post(
#             f"/phonebook/associations/{association.id}/picture",
#             files={"image": ("logo.png", image, "image/png")},
#             headers={"Authorization": f"Bearer {token_BDE}"},
#         )
#     assert response.status_code == 201


# def test_create_association_picture_simple():
#     with Path.open("assets/images/default_association_picture.png", "rb") as image:
#         response = client.post(
#             f"/phonebook/associations/{association.id}/picture",
#             files={"image": ("logo.png", image, "image/png")},
#             headers={"Authorization": f"Bearer {token_simple}"},
#         )
#     assert response.status_code == 403


# def test_get_association_picture_simple():
#     response = client.get(
#         f"/phonebook/associations/{association.id}/picture",
#         headers={"Authorization": f"Bearer {token_simple}"},
#     )
#     assert response.status_code == 200
