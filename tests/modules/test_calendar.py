import datetime
import uuid
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.associations import models_associations
from app.core.groups import models_groups
from app.core.users import models_users
from app.modules.calendar import models_calendar
from app.modules.calendar.endpoints_calendar import CalendarPermissions
from app.modules.calendar.types_calendar import Decision
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

admin_group: models_groups.CoreGroup
group_amap: models_groups.CoreGroup
group_bde: models_groups.CoreGroup

calendar_event: models_calendar.Event
calendar_event_to_delete: models_calendar.Event
confirmed_calendar_event: models_calendar.Event

association: models_associations.CoreAssociation

calendar_user_admin: models_users.CoreUser
calendar_user_simple: models_users.CoreUser
token_bde: str
token_admin: str
token_simple: str
token_amap: str

simple_user_ical_secret = "simple_user_ical_secret"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_group, group_amap
    admin_group = await create_groups_with_permissions(
        [CalendarPermissions.manage_events, CalendarPermissions.create_ical],
        "calendar_manager",
    )
    group_amap = await create_groups_with_permissions(
        [],
        "group_amap",
    )
    group_bde = await create_groups_with_permissions(
        [],
        "group_bde",
    )
    global calendar_user_admin
    calendar_user_admin = await create_user_with_groups(
        [admin_group.id],
    )

    global token_admin
    token_admin = create_api_access_token(calendar_user_admin)

    calendar_user_simple = await create_user_with_groups([])
    global token_simple
    token_simple = create_api_access_token(calendar_user_simple)

    calendar_user_amap = await create_user_with_groups([group_amap.id])
    global token_amap
    token_amap = create_api_access_token(calendar_user_amap)

    calendar_user_bde = await create_user_with_groups([group_bde.id])
    global token_bde
    token_bde = create_api_access_token(calendar_user_bde)

    global association
    association = models_associations.CoreAssociation(
        id=uuid.uuid4(),
        name="Eclair",
        group_id=group_amap.id,
    )
    await add_object_to_db(association)

    global calendar_event
    calendar_event = models_calendar.Event(
        id=uuid.uuid4(),
        name="Dojo",
        association_id=association.id,
        applicant_id=calendar_user_bde.id,
        start=datetime.datetime.fromisoformat("2022-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2022-09-22T23:00:00Z"),
        all_day=False,
        location="Skylab",
        description="Apprendre à coder !",
        decision=Decision.pending,
        recurrence_rule=None,
        ticket_url_opening=datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(days=6),
        ticket_url="url",
        notification=False,
    )
    await add_object_to_db(calendar_event)

    global confirmed_calendar_event
    confirmed_calendar_event = models_calendar.Event(
        id=uuid.uuid4(),
        name="Dojo",
        association_id=association.id,
        applicant_id=calendar_user_bde.id,
        start=datetime.datetime.fromisoformat("2022-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2022-09-22T23:00:00Z"),
        all_day=False,
        location="Skylab",
        description="Apprendre à coder !",
        decision=Decision.approved,
        recurrence_rule=None,
        ticket_url_opening=datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(days=6),
        ticket_url="url",
        notification=False,
    )
    await add_object_to_db(confirmed_calendar_event)

    global calendar_event_to_delete
    calendar_event_to_delete = models_calendar.Event(
        id=uuid.uuid4(),
        name="Dojo",
        association_id=association.id,
        applicant_id=calendar_user_simple.id,
        start=datetime.datetime.fromisoformat("2022-09-22T20:00:00Z"),
        end=datetime.datetime.fromisoformat("2022-09-22T23:00:00Z"),
        all_day=False,
        location="Skylab",
        description="Apprendre à coder !",
        decision=Decision.pending,
        recurrence_rule=None,
        ticket_url_opening=None,
        ticket_url=None,
        notification=False,
    )
    await add_object_to_db(calendar_event_to_delete)

    secret = models_calendar.IcalSecret(
        user_id=calendar_user_simple.id,
        secret=simple_user_ical_secret,
    )
    await add_object_to_db(secret)


def test_get_all_events(client: TestClient) -> None:
    response = client.get(
        "/calendar/events/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_confirmed_events(client: TestClient) -> None:
    response = client.get(
        "/calendar/events/confirmed",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_association_events_member_of_association(client: TestClient) -> None:
    response = client.get(
        f"/calendar/events/associations/{association.id}",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_association_events_not_member_of_association(client: TestClient) -> None:
    response = client.get(
        f"/calendar/events/associations/{association.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_event_by_id(client: TestClient) -> None:
    response = client.get(
        f"/calendar/events/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_event_by_id_pending_but_not_member_of_association(
    client: TestClient,
) -> None:
    response = client.get(
        f"/calendar/events/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_nonexistent_event(client: TestClient) -> None:
    response = client.get(
        f"/calendar/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404, response.text


def test_get_ticket_url_before(client: TestClient) -> None:
    response = client.get(
        f"/calendar/events/{calendar_event.id}/ticket-url",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 400, response.text


def test_get_ticket_url_after(client: TestClient) -> None:
    response = client.get(
        f"/calendar/events/{confirmed_calendar_event.id}/ticket-url",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ticket_url"] == "url"


def test_create_picture(client: TestClient) -> None:
    with Path("assets/images/default_advert.png").open("rb") as image:
        response = client.post(
            f"/calendar/events/{calendar_event.id}/image",
            files={"image": ("advert.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_amap}"},
        )

    assert response.status_code == 204


def test_add_event(client: TestClient) -> None:
    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "association_id": str(association.id),
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "all_day": False,
            "location": "Skylab",
            "description": "Apprendre à coder !",
            "notification": False,
        },
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 201


def test_add_event_with_missing_ticket_field(client: TestClient) -> None:
    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "association_id": str(association.id),
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "all_day": False,
            "location": "Skylab",
            "description": "Apprendre à coder !",
            "ticket_url_opening": "2019-08-24T14:15:22Z",
            "notification": False,
        },
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 422

    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "association_id": str(association.id),
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "all_day": False,
            "location": "Skylab",
            "description": "Apprendre à coder !",
            "ticket_url": "https://example.com/ticket",
            "notification": False,
        },
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 422


def test_add_event_non_member_of_association(client: TestClient) -> None:
    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "association_id": str(association.id),
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "all_day": False,
            "location": "Skylab",
            "description": "Apprendre à coder !",
            "notification": False,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_add_event_non_existing_association(client: TestClient) -> None:
    response = client.post(
        "/calendar/events/",
        json={
            "name": "Dojo",
            "association_id": str(uuid.uuid4()),
            "start": "2019-08-24T14:15:22Z",
            "end": "2019-08-24T14:15:22Z",
            "all_day": False,
            "location": "Skylab",
            "description": "Apprendre à coder !",
            "notification": False,
        },
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 404


def test_edit_event(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{calendar_event.id}",
        json={"description": "Apprendre à programmer"},
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 204


def test_edit_event_with_missing_ticket_field(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{calendar_event_to_delete.id}",
        json={
            "ticket_url_opening": "2019-08-24T14:15:22Z",
        },
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 400

    response = client.patch(
        f"/calendar/events/{calendar_event_to_delete.id}",
        json={
            "ticket_url": "https://example.com/ticket",
        },
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 400


def test_edit_event_not_member(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{confirmed_calendar_event.id}",
        json={"description": "Apprendre à programmer"},
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_decline_event(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{calendar_event.id}/reply/declined",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_approve_event(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{calendar_event.id}/reply/approved",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_approve_non_existing_event(client: TestClient) -> None:
    response = client.patch(
        f"/calendar/events/{uuid.uuid4()}/reply/approved",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404, response.text


def test_delete_event(client: TestClient) -> None:
    """Test if an admin can delete an event."""
    response = client.delete(
        f"/calendar/events/{calendar_event_to_delete.id}",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 204


def test_delete_non_existing_event(client: TestClient) -> None:
    """Test if an admin can delete an event."""
    response = client.delete(
        f"/calendar/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 404


def test_delete_event_unauthorized_user(client: TestClient) -> None:
    """Test if a simple user can't delete an event."""
    response = client.delete(
        f"/calendar/events/{calendar_event.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_ical_url(client: TestClient) -> None:
    """Test if a simple user can get the iCal URL for an event."""
    response = client.get(
        "/calendar/ical-url",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 200
    data = response.json()

    response2 = client.get(
        "/calendar/ical-url",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2 == data


def test_recreate_ical(client: TestClient) -> None:
    response = client.post(
        "/calendar/ical/create",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_get_ical(client: TestClient) -> None:
    """Test if a simple user can get the iCal URL for an event."""
    response = client.get(
        f"/calendar/ical?secret={simple_user_ical_secret}",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 200


def test_get_ical_invalid_secret(client: TestClient) -> None:
    """Test if a simple user can get the iCal URL for an event."""
    response = client.get(
        "/calendar/ical?secret=invalid",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 403
