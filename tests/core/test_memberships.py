import uuid
from datetime import UTC, date, datetime, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.groups.groups_type import GroupType
from app.core.memberships import models_memberships
from app.core.users import models_users
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

bde_group: models_groups.CoreGroup
bds_group: models_groups.CoreGroup
dummy_group_1: models_groups.CoreGroup
dummy_group_2: models_groups.CoreGroup

user: models_users.CoreUser
admin_user: models_users.CoreUser
bde_user: models_users.CoreUser

token_user: str
token_admin: str
token_bde: str
aeecl_association_membership: models_memberships.CoreAssociationMembership
useecl_association_membership: models_memberships.CoreAssociationMembership
user_membership: models_memberships.CoreAssociationUserMembership
useecl_user_membership: models_memberships.CoreAssociationUserMembership


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global bde_group, bds_group, dummy_group_1, dummy_group_2
    bde_group = await create_groups_with_permissions(
        [],
        "BDE Group",
    )
    bds_group = await create_groups_with_permissions(
        [],
        "BDS Group",
    )
    dummy_group_1 = await create_groups_with_permissions(
        [],
        "Dummy Group 1",
    )
    dummy_group_2 = await create_groups_with_permissions(
        [],
        "Dummy Group 2",
    )

    global user, admin_user, bde_user
    user = await create_user_with_groups([])
    admin_user = await create_user_with_groups(
        [GroupType.admin],
    )
    bde_user = await create_user_with_groups(
        [bde_group.id],
    )

    global token_user, token_admin, token_bde
    token_user = create_api_access_token(user)
    token_admin = create_api_access_token(admin_user)
    token_bde = create_api_access_token(bde_user)

    global aeecl_association_membership, useecl_association_membership
    aeecl_association_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="AEECL",
        manager_group_id=bde_group.id,
    )
    await add_object_to_db(aeecl_association_membership)
    useecl_association_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="USEECL",
        manager_group_id=bds_group.id,
    )
    await add_object_to_db(useecl_association_membership)

    global user_membership, useecl_user_membership
    user_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(user_membership)

    useecl_user_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=100),
        end_date=datetime.now(tz=UTC).date(),
    )
    await add_object_to_db(useecl_user_membership)


def test_get_association_memberships(client: TestClient):
    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]
    assert str(useecl_association_membership.id) in [x["id"] for x in response.json()]


def test_create_association_membership_user(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_1.id,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_association_membership_admin(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_1.id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])
    membership_name = response.json()["name"]
    membership_group_id = response.json()["manager_group_id"]

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership_id) in [x["id"] for x in response.json()]
    assert membership_name in [x["name"] for x in response.json()]
    assert membership_group_id in [x["manager_group_id"] for x in response.json()]


def test_delete_association_membership_user(client: TestClient):
    response = client.delete(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]


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
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]


async def test_delete_association_membership_admin(client: TestClient):
    new_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Random Association1",
        manager_group_id=dummy_group_1.id,
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership.id) not in [x["id"] for x in response.json()]


def test_patch_association_membership_user(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_2.id,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert aeecl_association_membership.name in [x["name"] for x in response.json()]
    assert aeecl_association_membership.manager_group_id in [
        x["manager_group_id"] for x in response.json()
    ]


async def test_patch_association_membership_admin(client: TestClient):
    new_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Random Association2",
        manager_group_id=dummy_group_1.id,
    )
    await add_object_to_db(new_membership)

    new_name = "Random Association3"
    new_group_id = dummy_group_2.id
    response = client.patch(
        f"/memberships/{new_membership.id}",
        json={
            "name": new_name,
            "manager_group_id": new_group_id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert new_name in [x["name"] for x in response.json()]
    assert new_group_id in [x["manager_group_id"] for x in response.json()]


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


def test_get_memberships_by_user_id_manager(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) in [x["id"] for x in response.json()]
    assert str(useecl_user_membership.id) not in [x["id"] for x in response.json()]


def test_get_association_membership_by_user_id_manager(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(user_membership.id) in [x["id"] for x in response.json()]


async def test_get_membership_with_date_filter(client: TestClient):
    today = datetime.now(tz=UTC).date()
    new_membership1 = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=10),
    )
    new_membership2 = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=today - timedelta(days=20),
        end_date=today + timedelta(days=20),
    )

    await add_object_to_db(new_membership1)
    await add_object_to_db(new_membership2)
    membership_ids = [
        new_membership1.id,
        new_membership2.id,
    ]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    for membership_id in membership_ids:
        assert str(membership_id) in [x["id"] for x in response.json()]

    minus_fifteen_days = today - timedelta(days=15)
    plus_fifteen_days = today + timedelta(days=15)

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?minimalStartDate={minus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) in [x["id"] for x in response.json()]
    assert str(new_membership2.id) not in [x["id"] for x in response.json()]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?maximalStartDate={minus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) not in [x["id"] for x in response.json()]
    assert str(new_membership2.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?minimalEndDate={plus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) not in [x["id"] for x in response.json()]
    assert str(new_membership2.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?maximalEndDate={plus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) in [x["id"] for x in response.json()]
    assert str(new_membership2.id) not in [x["id"] for x in response.json()]


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


def test_create_user_membership_wrong_association_id(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(uuid.uuid4()),
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_create_user_membership_with_wrong_dates(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(date(2028, 6, 1)),
            "end_date": str(date(2024, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_user_membership_with_overlapping_dates(client: TestClient):
    today = datetime.now(tz=UTC).date()

    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(aeecl_association_membership.id),
            "start_date": str(today),
            "end_date": str(today + timedelta(days=365)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_user_membership_admin(client: TestClient):
    today = datetime.now(tz=UTC).date()
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(today - timedelta(days=1000)),
            "end_date": str(today - timedelta(days=750)),
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


def test_create_user_membership_manager(client: TestClient):
    today = datetime.now(tz=UTC).date()
    response = client.post(
        f"/memberships/users/{bde_user.id}",
        json={
            "association_membership_id": str(aeecl_association_membership.id),
            "start_date": str(today - timedelta(days=1000)),
            "end_date": str(today - timedelta(days=750)),
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/memberships/users/{bde_user.id}",
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
    new_membership = models_memberships.CoreAssociationUserMembership(
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


async def test_delete_user_membership_manager(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=bde_user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/users/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership.id) not in [x["id"] for x in response.json()]


def test_patch_user_membership_user(client: TestClient):
    response = client.patch(
        f"/memberships/users/{user_membership.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_patch_user_membership_wrong_id(client: TestClient):
    response = client.patch(
        f"/memberships/users/{uuid.uuid4()}",
        json={
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_patch_user_membership_with_wrong_dates(client: TestClient):
    response = client.patch(
        f"/memberships/users/{user_membership.id}",
        json={
            "start_date": str(date(2028, 6, 1)),
            "end_date": str(date(2024, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


async def test_patch_user_membership_admin_overlapping_dates(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() + timedelta(days=20),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=70),
    )
    await add_object_to_db(new_membership)

    new_start_date = str(datetime.now(tz=UTC).date() - timedelta(days=50))
    new_end_date = str(datetime.now(tz=UTC).date() + timedelta(days=50))

    response = client.patch(
        f"/memberships/users/{new_membership.id}",
        json={
            "start_date": new_start_date,
            "end_date": new_end_date,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


async def test_patch_user_membership_admin(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=user_membership.end_date + timedelta(days=90),
        end_date=user_membership.end_date + timedelta(days=500),
    )
    await add_object_to_db(new_membership)

    new_start_date = str(user_membership.end_date + timedelta(days=100))
    new_end_date = str(user_membership.end_date + timedelta(days=1000))
    response = client.patch(
        f"/memberships/users/{new_membership.id}",
        json={
            "start_date": new_start_date,
            "end_date": new_end_date,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    membership = next(x for x in response.json() if x["id"] == str(new_membership.id))
    assert new_start_date == membership["start_date"]
    assert new_end_date == membership["end_date"]
    assert user.id == membership["user_id"]
    assert new_membership.id == uuid.UUID(membership["id"])


async def test_patch_user_membership_manager(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=bde_user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=user_membership.end_date + timedelta(days=90),
        end_date=user_membership.end_date + timedelta(days=500),
    )
    await add_object_to_db(new_membership)

    new_start_date = str(user_membership.end_date + timedelta(days=100))
    new_end_date = str(user_membership.end_date + timedelta(days=1000))
    response = client.patch(
        f"/memberships/users/{new_membership.id}",
        json={
            "start_date": new_start_date,
            "end_date": new_end_date,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/users/{bde_user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    membership = next(x for x in response.json() if x["id"] == str(new_membership.id))
    assert new_start_date == membership["start_date"]
    assert new_end_date == membership["end_date"]
    assert bde_user.id == membership["user_id"]
    assert new_membership.id == uuid.UUID(membership["id"])


def test_post_batch_user_memberships_user(client: TestClient):
    response = client.post(
        f"/memberships/{aeecl_association_membership.id}/add-batch/",
        json=[
            {
                "user_email": user.email,
                "start_date": str(date(2024, 6, 1)),
                "end_date": str(date(2028, 6, 1)),
            },
            {
                "user_email": user.email,
                "start_date": str(date(2024, 6, 1)),
                "end_date": str(date(2028, 6, 1)),
            },
        ],
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_post_batch_user_memberships_admin(client: TestClient):
    today = datetime.now(tz=UTC).date()
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=today - timedelta(days=1000),
        end_date=today + timedelta(days=365),
    )
    await add_object_to_db(new_membership)

    response = client.post(
        f"/memberships/{aeecl_association_membership.id}/add-batch/",
        json=[
            {
                "user_email": user.email,
                "start_date": str(today - timedelta(days=1000)),
                "end_date": str(today + timedelta(days=365)),
            },
            {
                "user_email": user.email,
                "start_date": str(date(2018, 6, 1)),
                "end_date": str(date(2019, 6, 1)),
            },
        ],
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    aeecl_memberships = [
        x
        for x in response.json()
        if x["association_membership_id"] == str(aeecl_association_membership.id)
    ]
    seen = False
    for membership in aeecl_memberships:
        if membership["start_date"] == str(today - timedelta(days=1000)) and membership[
            "end_date"
        ] == str(today + timedelta(days=365)):
            assert not seen
            seen = True
    assert seen
    membership = next(
        (
            x
            for x in aeecl_memberships
            if x["start_date"] == str(date(2018, 6, 1))
            and x["end_date"] == str(date(2019, 6, 1))
        ),
        None,
    )
    assert membership is not None
