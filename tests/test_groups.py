import uuid
from datetime import UTC, date, datetime, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.types.membership import AvailableAssociationMembership
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser
user_test: models_core.CoreUser

id_test_eclair = "8aab79e7-1e15-456d-b6e2-11e4e9f77e4f"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, user_test

    eclair = models_core.CoreGroup(
        id=id_test_eclair,
        name="test_eclair",
        description="Les meilleurs",
    )
    await add_object_to_db(eclair)

    admin_user = await create_user_with_groups([GroupType.admin])
    user_test = await create_user_with_groups([])

    aeecl_membership_admin = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        membership=AvailableAssociationMembership.aeecl,
        start_date=date(2021, 9, 5),
        end_date=date(2022, 9, 5),
    )
    useecl_membership_admin = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        membership=AvailableAssociationMembership.useecl,
        start_date=date(2021, 9, 5),
        end_date=date(2027, 9, 5),
    )
    aeecl_membership_test = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        user_id=user_test.id,
        membership=AvailableAssociationMembership.aeecl,
        start_date=date(2021, 9, 5),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(aeecl_membership_admin)
    await add_object_to_db(useecl_membership_admin)
    await add_object_to_db(aeecl_membership_test)


def test_read_groups(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.get(
        "/groups/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_read_group(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.get(
        f"/groups/{id_test_eclair}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_eclair"


def test_create_group(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.post(
        "/groups/",
        json={
            "name": "Group",
            "description": "A new group",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_update_group(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.patch(
        f"/groups/{id_test_eclair}",
        json={
            "name": "Group ECLAIR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_create_membership(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.post(
        "/groups/membership",
        json={
            "user_id": admin_user.id,
            "group_id": id_test_eclair,
            "description": "Group membership",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_delete_membership(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.request(
        method="DELETE",
        url="/groups/membership",
        json={
            "user_id": admin_user.id,
            "group_id": id_test_eclair,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_sync_group_with_association_membership(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.patch(
        f"/groups/{id_test_eclair}/sync/AEECL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/groups/{id_test_eclair}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 1
    assert data["members"][0]["id"] == str(user_test.id)
