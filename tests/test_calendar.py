import datetime
import uuid

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.booking.types_booking import Decision
from app.modules.calendar import models_calendar
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

calendar_event: models_calendar.Event
calendar_event_to_delete: models_calendar.Event
calendar_user_bde: models_core.CoreUser
calendar_user_simple: models_core.CoreUser
token_bde: str
token_simple: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global calendar_user_bde
    calendar_user_bde = await create_user_with_groups(
        [GroupType.student, GroupType.BDE],
    )

    global token_bde
    token_bde = create_api_access_token(calendar_user_bde)

    global calendar_user_simple
    calendar_user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(calendar_user_simple)

    global calendar_event
    calendar_event = models_calendar.Event(
        id=str(uuid.uuid4()),
        name="Dojo",
        organizer="Eclair",
        applicant_id=calendar_user_bde.id,
        start=datetime.datetime.fromisoformat("2022-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2022-09-22T23:00:00Z"),
        all_day=False,
        location="Skylab",
        type="Event AE",
        description="Apprendre à coder !",
        decision=Decision.pending,
    )
    await add_object_to_db(calendar_event)

    global calendar_event_to_delete
    calendar_event_to_delete = models_calendar.Event(
        id=str(uuid.uuid4()),
        name="Dojo",
        organizer="Eclair",
        applicant_id=calendar_user_simple.id,
        start=datetime.datetime.fromisoformat("2022-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2022-09-22T23:00:00Z"),
        all_day=False,
        location="Skylab",
        type="Event AE",
        description="Apprendre à coder !",
        decision=Decision.pending,
    )
    await add_object_to_db(calendar_event_to_delete)


def test_get_all_events(client: TestClient) -> None:
    global token_bde

    response = client.get(
        "/calendar/events/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200


def test_get_event(client: TestClient) -> None:
    global token_bde

    response = client.get(
        f"/calendar/events/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200


def test_get_nonexistent_event(client: TestClient) -> None:
    response = client.get(
        "/calendar/events/bad_id",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_add_event(client: TestClient) -> None:
    global token_bde

    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "organizer": "Eclair",
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "all_day": False,
            "location": "Skylab",
            "type": "Event AE",
            "description": "Apprendre à coder !",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201


def test_add_event_missing_parameter(client: TestClient) -> None:
    """Test to add an event but a parameter is missing. `start` is missing"""
    global token_bde

    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "organizer": "Eclair",
            "end": "2019-08-24T14:15:22Z",
            "location": "Skylab",
            "type": "Event AE",
            "description": "Apprendre à coder !",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 422


def test_edit_event(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{calendar_event.id}",
        json={"description": "Apprendre à programmer"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_delete_event(client: TestClient) -> None:
    """Test if an admin can delete an event."""

    global token_bde

    response = client.delete(
        f"/calendar/events/{calendar_event_to_delete.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_delete_event_unauthorized_user(client: TestClient) -> None:
    """Test if a simple user can't delete an event."""

    global token_simple

    response = client.delete(
        f"/calendar/events/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_decline_event(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{calendar_event.id}/reply/declined",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


def test_approve_event(client: TestClient) -> None:
    global token_bde
    response = client.patch(
        f"/calendar/events/{calendar_event.id}/reply/approved",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204
