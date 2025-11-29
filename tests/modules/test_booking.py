import datetime
import uuid

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.booking import models_booking
from app.modules.booking.types_booking import Decision
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

booking_id: str

booking: models_booking.Booking
booking_to_delete: models_booking.Booking
room: models_booking.Room
room_to_delete: models_booking.Room
manager: models_booking.Manager
manager_to_delete: models_booking.Manager
admin_user: models_users.CoreUser
manager_user: models_users.CoreUser
simple_user: models_users.CoreUser

token_admin: str
token_manager: str
token_simple: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user
    admin_user = await create_user_with_groups([GroupType.admin])

    global token_admin
    token_admin = create_api_access_token(admin_user)

    global manager_user
    manager_user = await create_user_with_groups(
        [GroupType.BDE],
    )

    global token_manager
    token_manager = create_api_access_token(manager_user)

    global simple_user
    simple_user = await create_user_with_groups([])

    global token_simple
    token_simple = create_api_access_token(simple_user)

    global manager
    manager = models_booking.Manager(
        id=str(uuid.uuid4()),
        name="BDE",
        group_id=GroupType.BDE,
    )
    await add_object_to_db(manager)

    global manager_to_delete
    manager_to_delete = models_booking.Manager(
        id=str(uuid.uuid4()),
        name="Planet",
        group_id=GroupType.amap,
    )
    await add_object_to_db(manager_to_delete)

    global room
    room = models_booking.Room(
        id=str(uuid.uuid4()),
        name="Foyer",
        manager_id=manager.id,
    )
    await add_object_to_db(room)

    global room_to_delete
    room_to_delete = models_booking.Room(
        id=str(uuid.uuid4()),
        name="Test",
        manager_id=manager.id,
    )
    await add_object_to_db(room_to_delete)

    global booking_id
    booking_id = str(uuid.uuid4())

    global booking
    booking = models_booking.Booking(
        id=booking_id,
        reason="HH",
        start=datetime.datetime.fromisoformat("2023-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2023-09-22T23:00:00Z"),
        creation=datetime.datetime.fromisoformat("2023-09-10T10:00:00Z"),
        room_id=room.id,
        key=True,
        decision=Decision.approved,
        applicant_id=simple_user.id,
        entity="dbs",
        note=None,
        recurrence_rule=None,
    )
    await add_object_to_db(booking)

    global booking_to_delete
    booking_to_delete = models_booking.Booking(
        id=str(uuid.uuid4()),
        reason="Test",
        start=datetime.datetime.fromisoformat("2023-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2023-09-22T23:00:00Z"),
        creation=datetime.datetime.fromisoformat("2023-09-10T10:00:00Z"),
        room_id=room.id,
        key=True,
        decision=Decision.pending,
        applicant_id=simple_user.id,
        entity="Test",
        note=None,
        recurrence_rule=None,
    )
    await add_object_to_db(booking_to_delete)


def test_get_managers(client: TestClient) -> None:
    response = client.get(
        "/booking/managers",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_post_manager(client: TestClient) -> None:
    response = client.post(
        "/booking/managers",
        json={
            "id": str(uuid.uuid4()),
            "name": "Admin",
            "group_id": GroupType.admin.value,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_edit_manager(client: TestClient) -> None:
    response = client.patch(
        f"/booking/managers/{manager_to_delete.id}",
        json={"name": "Test"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    response = client.patch(
        f"/booking/managers/{manager_to_delete.id}",
        json={"group_id": GroupType.cinema.value},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_manager(client: TestClient) -> None:
    response = client.delete(
        f"/booking/managers/{manager_to_delete.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_get_user_managers(client: TestClient) -> None:
    response = client.get(
        "/booking/managers/users/me",
        headers={"Authorization": f"Bearer {token_manager}"},
    )
    assert response.status_code == 200


def test_get_user_bookings_manage(client: TestClient) -> None:
    response = client.get(
        "/booking/bookings/users/me/manage",
        headers={"Authorization": f"Bearer {token_manager}"},
    )
    assert response.status_code == 200


def test_get_user_bookings_manage_confirmed(client: TestClient) -> None:
    response = client.get(
        "/booking/bookings/confirmed/users/me/manage",
        headers={"Authorization": f"Bearer {token_manager}"},
    )
    assert response.status_code == 200
    assert booking_id in [booking["id"] for booking in response.json()]
    assert response.json()[0]["applicant"].get("name", None) == simple_user.name
    assert response.json()[0]["applicant"].get("email", None) == simple_user.email


def test_get_bookings_confirmed(client: TestClient) -> None:
    response = client.get(
        "/booking/bookings/confirmed",
        headers={"Authorization": f"Bearer {token_manager}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["applicant"].get("name", None) == simple_user.name
    assert response.json()[0]["applicant"].get("email", None) is None


def test_get_user_bookings(client: TestClient) -> None:
    response = client.get(
        "/booking/bookings/users/me",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_post_bookings(client: TestClient) -> None:
    response = client.post(
        "/booking/bookings",
        json={
            "reason": "Test",
            "start": "2022-09-15T08:00:00Z",
            "end": "2022-09-15T09:00:00Z",
            "creation": "2022-09-15T07:00:00Z",
            "note": "do",
            "room_id": room.id,
            "key": True,
            "multipleDay": False,
            "recurring": False,
            "entity": "TEST",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201


def test_edit_booking(client: TestClient) -> None:
    response = client.patch(
        f"/booking/bookings/{booking.id}",
        json={"reason": "Pas un test"},
        headers={"Authorization": f"Bearer {token_manager}"},
    )
    assert response.status_code == 204


def test_reply_booking(client: TestClient) -> None:
    response = client.patch(
        f"/booking/bookings/{booking.id}/reply/declined",
        headers={"Authorization": f"Bearer {token_manager}"},
    )
    assert response.status_code == 204


def test_delete_booking(client: TestClient) -> None:
    response = client.delete(
        f"/booking/bookings/{booking_to_delete.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204


def test_get_room(client: TestClient) -> None:
    response = client.get(
        "/booking/rooms",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    json = response.json()
    assert len(json) == 2


def test_post_room(client: TestClient) -> None:
    response = client.post(
        "/booking/rooms",
        json={"name": "Local JE", "manager_id": manager.id},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_edit_room(client: TestClient) -> None:
    response = client.patch(
        f"/booking/rooms/{room.id}",
        json={"name": "Foyer", "manager_id": manager.id},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_room(client: TestClient) -> None:
    # create a room to delete
    response = client.delete(
        f"/booking/rooms/{room_to_delete.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
