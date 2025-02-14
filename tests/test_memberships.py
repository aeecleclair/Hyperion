import uuid
from datetime import UTC, date, datetime, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

user: models_core.CoreUser
admin_user: models_core.CoreUser

token_user: str
token_admin: str

aeecl_association_membership: models_core.CoreAssociationMembership
useecl_association_membership: models_core.CoreAssociationMembership
user_membership: models_core.CoreAssociationUserMembership


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global user, admin_user
    user = await create_user_with_groups([])
    admin_user = await create_user_with_groups(
        [GroupType.admin],
    )

    global token_user, token_admin
    token_user = create_api_access_token(user)
    token_admin = create_api_access_token(admin_user)

    global aeecl_association_membership, useecl_association_membership
    aeecl_association_membership = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="AEECL",
        group_id=GroupType.BDE,
    )
    await add_object_to_db(aeecl_association_membership)
    useecl_association_membership = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="USEECL",
        group_id=GroupType.BDS,
    )
    await add_object_to_db(useecl_association_membership)

    global user_membership
    user_membership = models_core.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(user_membership)


def test_get_association_memberships(client: TestClient):
    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]
    assert str(useecl_association_membership.id) in [x["id"] for x in response.json()]


def test_get_association_membership_by_id(client: TestClient):
    response = client.get(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(aeecl_association_membership.id)
    assert response.json()["name"] == "AEECL"
    assert len(response.json()["users_memberships"]) == 1


def test_get_association_membership_by_id_wrong_id(client: TestClient):
    response = client.get(
        f"/memberships/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 404


def test_create_association_membership_user(client: TestClient):
    response = client.post(
        "/memberships",
        json={"name": "Random Association"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_association_membership_admin(client: TestClient):
    response = client.post(
        "/memberships",
        json={"name": "Random Association"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/memberships/{membership_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(membership_id)
    assert response.json()["name"] == "Random Association"


def test_delete_association_membership_user(client: TestClient):
    response = client.delete(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200


def test_delete_association_membership_wrong_id(client: TestClient):
    response = client.delete(
        f"/memberships/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_delete_association_membership_with_users(client: TestClient):
    response = client.delete(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400

    response = client.get(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "AEECL"


async def test_delete_association_membership_admin(client: TestClient):
    new_membership = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Random Association",
        group_id=GroupType.AE,
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_patch_association_membership_user(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "AEECL"


async def test_patch_association_membership_admin(client: TestClient):
    new_membership = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Random Association",
        group_id=GroupType.AE,
    )
    await add_object_to_db(new_membership)

    response = client.patch(
        f"/memberships/{new_membership.id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.get(
        f"/memberships/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_get_memberships_by_user_id_user(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) in [x["id"] for x in response.json()]


def test_get_memberships_by_user_id_admin(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) in [x["id"] for x in response.json()]


def test_get_membership_with_date_filter(client: TestClient):
    today = datetime.now(tz=UTC).date()
    response = client.get(
        f"/memberships/users/{user.id}?minimalDate={today.strftime('%Y%m%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) in [x["id"] for x in response.json()]

    five_years_later = today + timedelta(days=365 * 5)
    response = client.get(
        f"/memberships/users/{user.id}?minimalDate={five_years_later.strftime('%Y%m%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) not in [x["id"] for x in response.json()]


def test_create_user_membership_user(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(aeecl_association_membership.id),
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_user_membership_admin(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(date(2000, 6, 1)),
            "end_date": str(date(2001, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership_id) in [x["id"] for x in response.json()]


def test_delete_user_membership_user(client: TestClient):
    response = client.delete(
        f"/memberships/users/{user_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) in [x["id"] for x in response.json()]


def test_delete_user_membership_wrong_id(client: TestClient):
    response = client.delete(
        f"/memberships/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


async def test_delete_user_membership_admin(client: TestClient):
    new_membership = models_core.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/users/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership.id) not in [x["id"] for x in response.json()]
