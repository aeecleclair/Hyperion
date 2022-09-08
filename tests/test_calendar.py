import datetime
import uuid

from app.main import app
from app.models import models_calendar, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

calendar_event: models_calendar.Event | None = None
calendar_user_bde: models_core.CoreUser | None = None
calendar_user_simple: models_core.CoreUser | None = None
token_admin: str = ""
token_simple: str = ""


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global calendar_user_bde
    async with TestingSessionLocal() as db:
        calendar_user_bde = await create_user_with_groups([GroupType.BDE], db=db)
        await db.commit()

    global token_admin
    token_admin = create_api_access_token(calendar_user_bde)

    global calendar_user_simple
    async with TestingSessionLocal() as db:
        calendar_user_simple = await create_user_with_groups([GroupType.student], db=db)
        await db.commit()

    global token_simple
    token_simple = create_api_access_token(calendar_user_simple)

    global calendar_event
    async with TestingSessionLocal() as db:
        calendar_event = models_calendar.Event(
            id=str(uuid.uuid4()),
            name="Dojo",
            organizer="Eclair",
            start=datetime.datetime.fromisoformat("2022-09-22T20:00:00"),
            end=datetime.datetime.fromisoformat("2022-09-22T23:00:00"),
            place="Skylab",
            type="Event AE",
            description="Apprendre à coder !",
            recurrence=False,
        )
        db.add(calendar_event)
        await db.commit()


def test_get_all_events():
    global token_admin

    response = client.get(
        "/calendar/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_event():
    global token_admin

    response = client.get(
        f"/calendar/event/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_nonexistent_event():
    response = client.get(
        "/calendar/event/bad_id",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_add_event():
    global token_admin

    response = client.post(
        "/calendar/event/",
        json={
            "name": "Dojo",
            "organizer": "Eclair",
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "place": "Skylab",
            "type": "Event AE",
            "description": "Apprendre à coder !",
            "recurrence": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_add_event_missing_parameter():
    """Test to add an event but a parameter is missing. `start` is missing"""
    global token_admin

    response = client.post(
        "/calendar/event/",
        json={
            "name": "Dojo",
            "organizer": "Eclair",
            "end": "2019-08-24T14:15:22Z",
            "place": "Skylab",
            "type": "Event AE",
            "description": "Apprendre à coder !",
            "recurrence": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 422


def test_add_event_unauthorized_user():
    """Test if a non-admin user can add an event."""
    global token_simple

    response = client.post(
        "/calendar/event/",
        json={
            "name": "Dojo",
            "organizer": "Eclair",
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "place": "Skylab",
            "type": "Event AE",
            "description": "Apprendre à coder !",
            "recurrence": False,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_event():
    """Test if an admin can delete an event."""

    global token_admin

    response = client.delete(
        f"/calendar/event/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_event_unauthorized_user():
    """Test if a simple user can't delete an event."""

    global token_simple

    response = client.delete(
        f"/calendar/event/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403
