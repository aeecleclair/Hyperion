import uuid
from pathlib import Path

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.phonebook import models_phonebook, schemas_phonebook
from app.modules.phonebook.types_phonebook import Kinds, RoleTags
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)

association: models_phonebook.Association | None = None
associations_to_delete_admin: models_phonebook.Association | None = None
associations_to_delete_simple: models_phonebook.Association | None = None

membership: models_phonebook.Membership | None = None
membership_to_delete_admin: models_phonebook.Membership | None = None
membership_to_delete_president: models_phonebook.Membership | None = None
membership_to_delete_simple: models_phonebook.Membership | None = None
phonebook_user_BDE: models_core.CoreUser | None = None
phonebook_user_president: models_core.CoreUser | None = None
phonebook_user_simple: models_core.CoreUser | None = None

token_BDE: str = ""
token_president: str = ""
token_simple: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global phonebook_user_BDE
    phonebook_user_BDE = await create_user_with_groups(
        [GroupType.student, GroupType.BDE],
    )

    global token_BDE
    token_BDE = create_api_access_token(phonebook_user_BDE)

    global phonebook_user_president
    phonebook_user_president = await create_user_with_groups([GroupType.student])

    global token_president
    token_president = create_api_access_token(phonebook_user_president)

    global phonebook_user_simple
    phonebook_user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(phonebook_user_simple)

    global association
    association = models_phonebook.Association(
        id=str(uuid.uuid4()),
        kind=Kinds.section_ae,
        name="ECLAIR",
        mandate_year=2023,
    )
    await add_object_to_db(association)

    global associations_to_delete_admin
    associations_to_delete_admin = models_phonebook.Association(
        id=str(uuid.uuid4()),
        kind=Kinds.association_independant,
        name="Nom",
        mandate_year=2023,
    )
    await add_object_to_db(associations_to_delete_admin)

    global associations_to_delete_simple
    associations_to_delete_simple = models_phonebook.Association(
        id=str(uuid.uuid4()),
        kind=Kinds.association_independant,
        name="Nom",
        mandate_year=2023,
    )
    await add_object_to_db(associations_to_delete_simple)

    global membership
    membership = models_phonebook.Membership(
        id=str(uuid.uuid4()),
        user_id=phonebook_user_president.id,
        association_id=association.id,
        role_tags=RoleTags.president.value,
        role_name="Chef",
        mandate_year=2023,
    )
    await add_object_to_db(membership)

    global membership_to_delete_admin
    membership_to_delete_admin = models_phonebook.Membership(
        id=str(uuid.uuid4()),
        user_id=phonebook_user_simple.id,
        association_id=association.id,
        role_tags="Lambda",
        role_name="Membre",
        mandate_year=2000,
    )
    await add_object_to_db(membership_to_delete_admin)

    global membership_to_delete_president
    membership_to_delete_president = models_phonebook.Membership(
        id=str(uuid.uuid4()),
        user_id=phonebook_user_simple.id,
        association_id=association.id,
        role_tags="Lambda",
        role_name="Membre",
        mandate_year=2001,
    )
    await add_object_to_db(membership_to_delete_president)

    global membership_to_delete_simple
    membership_to_delete_simple = models_phonebook.Membership(
        id=str(uuid.uuid4()),
        user_id=phonebook_user_simple.id,
        association_id=association.id,
        role_tags="Lambda",
        role_name="Membre",
        mandate_year=2002,
    )
    await add_object_to_db(membership_to_delete_simple)


# ---------------------------------------------------------------------------- #
#                                  Kinds tests                                 #
# ---------------------------------------------------------------------------- #
def test_get_all_association_kinds_simple():
    response = client.get(
        "/phonebook/associations/kinds",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------- #
#                                Roletags tests                                #
# ---------------------------------------------------------------------------- #
def test_get_all_roletags_simple():
    response = client.get(
        "/phonebook/roletags/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------- #
#                              Associations tests                              #
# ---------------------------------------------------------------------------- #
def test_get_all_associations():
    response = client.get(
        "/phonebook/associations/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


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
    assert response.status_code == 201


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


def test_update_association_admin():
    response = client.patch(
        f"/phonebook/associations/{association.id}",
        json={
            "name": "Bazar 1",
            "description": "Bazar modifié",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_update_association_president():
    response = client.patch(
        f"/phonebook/associations/{association.id}",
        json={
            "name": "Bazar 2",
            "description": "Bazar modifié",
        },
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 204


def test_update_association_simple():
    response = client.patch(
        f"/phonebook/associations/{association.id}/",
        json={
            "name": "Éclair",
            "description": "Foudroyante",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_association_admin():
    response = client.delete(
        f"/phonebook/associations/{associations_to_delete_admin.id}/",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_delete_association_simple():
    response = client.delete(
        f"/phonebook/associations/{associations_to_delete_simple.id}/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                               Memberships tests                              #
# ---------------------------------------------------------------------------- #
def test_add_membership_admin():
    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association.id,
            "mandate_year": 2023,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201


def test_add_membership_simple():
    response = client.post(
        "/phonebook/associations/memberships",
        json={
            "user_id": phonebook_user_simple.id,
            "association_id": association.id,
            "mandate_year": 2023,
            "role_name": "VP Emprunts",
            "role_tags": "VP Emprunts",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_update_membership_admin():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership.id}",
        json={
            "role_name": "Autre rôle",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_update_membership_president():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership.id}",
        json={
            "role_name": "Un super rôle",
        },
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 204


def test_update_membership_simple():
    response = client.patch(
        f"/phonebook/associations/memberships/{membership.id}",
        json={
            "role_name": "Encore un autre rôle",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_membership_admin():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership_to_delete_admin.id}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_delete_membership_president():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership_to_delete_president.id}",
        headers={"Authorization": f"Bearer {token_president}"},
    )
    assert response.status_code == 204


def test_delete_membership_simple():
    response = client.delete(
        f"/phonebook/associations/memberships/{membership_to_delete_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                                 Members tests                                #
# ---------------------------------------------------------------------------- #
def test_get_members_by_association_id_simple():
    response = client.get(
        f"/phonebook/associations/{association.id}/members/{association.mandate_year}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for member in response.json():
        assert isinstance(
            schemas_phonebook.MemberComplete(**member),
            schemas_phonebook.MemberComplete,
        )


def test_get_member_by_id_simple():
    response = client.get(
        f"phonebook/member/{phonebook_user_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert isinstance(
        schemas_phonebook.MemberComplete(**response.json()),
        schemas_phonebook.MemberComplete,
    )


# ---------------------------------------------------------------------------- #
#                                  Logos tests                                 #
# ---------------------------------------------------------------------------- #
def test_create_association_picture_admin():
    with Path.open("assets/images/default_association_picture.png", "rb") as image:
        response = client.post(
            f"/phonebook/associations/{association.id}/picture",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_BDE}"},
        )
    assert response.status_code == 201


def test_create_association_picture_simple():
    with Path.open("assets/images/default_association_picture.png", "rb") as image:
        response = client.post(
            f"/phonebook/associations/{association.id}/picture",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_simple}"},
        )
    assert response.status_code == 403


def test_get_association_picture_simple():
    response = client.get(
        f"/phonebook/associations/{association.id}/picture",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
