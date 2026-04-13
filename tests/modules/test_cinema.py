import datetime
import uuid

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.users import models_users
from app.modules.cinema import models_cinema
from app.modules.cinema.endpoints_cinema import CinemaPermissions
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

admin_group: models_groups.CoreGroup

session: models_cinema.Session
cinema_user_cinema: models_users.CoreUser
cinema_user_simple: models_users.CoreUser
token_cinema: str
token_simple: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_group
    admin_group = await create_groups_with_permissions(
        [CinemaPermissions.manage_sessions],
        "cinema_admin",
    )

    global cinema_user_cinema
    cinema_user_cinema = await create_user_with_groups([admin_group.id])

    global token_cinema
    token_cinema = create_api_access_token(cinema_user_cinema)

    global cinema_user_simple
    cinema_user_simple = await create_user_with_groups(
        [],
    )

    global token_simple
    token_simple = create_api_access_token(cinema_user_simple)

    global session
    session = models_cinema.Session(
        id=str(uuid.uuid4()),
        name="Titanic",
        start=datetime.datetime.fromisoformat("2022-10-22T20:00:00Z"),
        duration=194,
        overview="Southampton, 10 avril 1912. Le paquebot le plus grand et le plus moderne du monde, réputé pour son insubmersibilité, le « Titanic », appareille pour son premier voyage. Quatre jours plus tard, il heurte un iceberg. À son bord, un artiste pauvre et une grande bourgeoise tombent amoureux.",
        genre="Drame, Romance",
        year="1997",
    )
    await add_object_to_db(session)


def test_get_sessions(client: TestClient) -> None:
    response = client.get(
        "/cinema/sessions",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_post_session(client: TestClient) -> None:
    response = client.post(
        "/cinema/sessions",
        json={
            "name": "Les Tuches",
            "start": "2022-10-23T14:00:00Z",
            "duration": 90,
            "overview": "Synopsis...",
        },
        headers={"Authorization": f"Bearer {token_cinema}"},
    )
    assert response.status_code == 201


def test_edit_session(client: TestClient) -> None:
    response = client.patch(
        f"/cinema/sessions/{session.id}",
        json={"name": "Titanoc"},
        headers={"Authorization": f"Bearer {token_cinema}"},
    )
    assert response.status_code == 200


def test_delete_session(client: TestClient) -> None:
    response = client.delete(
        f"/cinema/sessions/{session.id}",
        headers={"Authorization": f"Bearer {token_cinema}"},
    )
    assert response.status_code == 204
