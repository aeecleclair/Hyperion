import pytest_asyncio

from app.models import models_core
from app.utils.types.groups_type import GroupType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import event_loop  # noqa
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser | None = None


id_eclair = "8aab79e7-1e15-456d-b6e2-11e4e9f77e4f"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_objects():
    global admin_user

    eclair = models_core.CoreGroup(
        id=id_eclair,
        name="eclair",
        description="Les meilleurs",
    )
    await add_object_to_db(eclair)

    admin_user = await create_user_with_groups([GroupType.admin])


def test_read_groups():
    token = create_api_access_token(admin_user)

    response = client.get(
        "/groups/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_read_group():
    token = create_api_access_token(admin_user)

    response = client.get(
        f"/groups/{id_eclair}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "eclair"


def test_create_group():
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


def test_update_group():
    token = create_api_access_token(admin_user)

    response = client.patch(
        f"/groups/{id_eclair}",
        json={
            "name": "Group ECLAIR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_create_membership():
    token = create_api_access_token(admin_user)

    response = client.post(
        "/groups/membership",
        json={
            "user_id": admin_user.id,
            "group_id": id_eclair,
            "description": "Group membership",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_delete_membership():
    token = create_api_access_token(admin_user)

    response = client.request(
        method="DELETE",
        url="/groups/membership",
        json={
            "user_id": admin_user.id,
            "group_id": id_eclair,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
