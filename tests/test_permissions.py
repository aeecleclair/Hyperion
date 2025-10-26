import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.groups.groups_type import GroupType
from app.core.permissions import models_permissions
from app.core.users import models_users
from app.modules.booking.endpoints_booking import BookingPermissions
from app.modules.cinema.endpoints_cinema import CinemaPermissions
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

group1: models_groups.CoreGroup
group2: models_groups.CoreGroup
group3: models_groups.CoreGroup

admin_user: models_users.CoreUser
admin_token: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global group1, group2, group3
    group1 = await create_groups_with_permissions(
        [BookingPermissions.manage_managers, CinemaPermissions.manage_sessions],
        "group1",
    )
    group2 = await create_groups_with_permissions(
        [BookingPermissions.manage_managers, BookingPermissions.manage_rooms],
        "group2",
    )
    group3 = await create_groups_with_permissions(
        [],
        "group3",
    )

    global admin_user
    admin_user = await create_user_with_groups([GroupType.admin])
    global admin_token
    admin_token = create_api_access_token(admin_user)


def test_read_permissions(client: TestClient) -> None:
    response = client.get(
        "/permissions/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_read_permission_by_name(client: TestClient) -> None:
    response = client.get(
        f"/permissions/{BookingPermissions.manage_managers.value}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_permission(client: TestClient) -> None:
    response = client.post(
        "/permissions/",
        json={
            "permission_name": BookingPermissions.manage_managers.value,
            "group_id": group3.id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/permissions/{BookingPermissions.manage_managers.value}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


async def test_delete_permission(client: TestClient) -> None:
    permission = models_permissions.CorePermission(
        permission_name=BookingPermissions.manage_rooms,
        group_id=group3.id,
    )
    await add_object_to_db(permission)
    response = client.request(
        method="DELETE",
        url="/permissions/",
        json={
            "permission_name": BookingPermissions.manage_rooms.value,
            "group_id": group3.id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204
