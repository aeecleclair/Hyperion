import datetime
import uuid

from app.main import app
from app.models import models_bdebooking, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

booking: models_bdebooking.Booking | None = None
room: models_bdebooking.Room | None = None
booking_user_bde: models_core.CoreUser | None = None
booking_user_simple: models_core.CoreUser | None = None
token_bde: str = ""
token_simple: str = ""


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global booking_user_bde
    async with TestingSessionLocal() as db:
        booking_user_bde = await create_user_with_groups([GroupType.BDE], db=db)
        await db.commit()

    global token_bde
    token_bde = create_api_access_token(booking_user_bde)

    global booking_user_simple
    async with TestingSessionLocal() as db:
        booking_user_simple = await create_user_with_groups([GroupType.student], db=db)
        await db.commit()

    global token_simple
    token_simple = create_api_access_token(booking_user_simple)

    global room
    async with TestingSessionLocal() as db:
        room = models_bdebooking.Room(id=str(uuid.uuid4()), name="Salle de Réunion")
        db.add(room)
        await db.commit()

    global booking
    async with TestingSessionLocal() as db:
        booking = models_bdebooking.Booking(
            id=str(uuid.uuid4()),
            reason="Réunion",
            start=datetime.datetime.fromisoformat("2022-09-22T20:00:00"),
            end=datetime.datetime.fromisoformat("2022-09-22T23:00:00"),
            room_id=room.id,
            key=True,
            decision="approved",
            applicant_id=booking_user_simple.id,
            entity="ECLAIR",
        )
        db.add(booking)
        await db.commit()


def test_get_rights():
    response = client.get(
        "/bdebooking/rights",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200


def test_get_bookings():
    response = client.get(
        "/bdebooking/bookings",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200


def test_get_user_bookings():
    response = client.get(
        f"/bdebooking/user/{booking_user_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_post_bookings():
    response = client.post(
        "/bdebooking/bookings",
        json={
            "reason": "Test",
            "start": "2022-09-15T08:00:00Z",
            "end": "2022-09-15T09:00:00Z",
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


def test_get_booking_by_id():
    response = client.get(
        f"/bdebooking/bookings/{booking.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200


def test_edit_booking():
    response = client.patch(
        f"/bdebooking/bookings/{booking.id}",
        json={"reason": "Pas un test"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_reply_booking():
    response = client.patch(
        f"/bdebooking/bookings/{booking.id}/reply/declined",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_delete_booking():
    response = client.delete(
        f"/bdebooking/bookings/{booking.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_get_room():
    response = client.get(
        "/bdebooking/rooms",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_room_id():
    response = client.get(
        f"/bdebooking/rooms/{room.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200


def test_post_room():
    response = client.post(
        "/bdebooking/rooms",
        json={"name": "Local JE"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201


def test_edit_room():
    response = client.patch(
        f"/bdebooking/rooms/{room.id}",
        json={"name": "Foyer"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_delete_room():
    # create a room to delete
    response = client.post(
        "/bdebooking/rooms",
        json={"name": "Local JE"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201
    room_id = response.json()["id"]

    response = client.delete(
        f"/bdebooking/rooms/{room_id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204
