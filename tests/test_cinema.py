import datetime
import uuid

from app.main import app
from app.models import models_cinema, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

session: models_cinema.Session | None = None
cinema_user_cinema: models_core.CoreUser | None = None
cinema_user_simple: models_core.CoreUser | None = None
token_cinema: str = ""
token_simple: str = ""


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global cinema_user_cinema
    async with TestingSessionLocal() as db:
        cinema_user_cinema = await create_user_with_groups([GroupType.cinema], db=db)
        await db.commit()

    global token_cinema
    token_cinema = create_api_access_token(cinema_user_cinema)

    global cinema_user_simple
    async with TestingSessionLocal() as db:
        cinema_user_simple = await create_user_with_groups([GroupType.student], db=db)
        await db.commit()

    global token_simple
    token_simple = create_api_access_token(cinema_user_simple)

    global session
    async with TestingSessionLocal() as db:
        session = models_cinema.Session(
            id=str(uuid.uuid4()),
            name="Titanic",
            start=datetime.datetime.fromisoformat("2022-10-22T20:00:00"),
            duration=194,
            overview="Southampton, 10 avril 1912. Le paquebot le plus grand et le plus moderne du monde, réputé pour son insubmersibilité, le « Titanic », appareille pour son premier voyage. Quatre jours plus tard, il heurte un iceberg. À son bord, un artiste pauvre et une grande bourgeoise tombent amoureux.",
            genre="Drame, Romance",
            tagline="Rien sur cette terre ne saurait les séparer.",
        )
        db.add(session)
        await db.commit()


def test_get_sessions():
    response = client.get(
        "/cinema/sessions",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_post_session():
    response = client.post(
        "/cinema/sessions",
        json={
            "name": "Les Tuches",
            "start": "2022-10-23T14:00:00Z",
            "duration": 90,
        },
        headers={"Authorization": f"Bearer {token_cinema}"},
    )
    assert response.status_code == 201


def test_edit_session():
    response = client.patch(
        f"/cinema/sessions/{session.id}",
        json={"name": "Titanoc"},
        headers={"Authorization": f"Bearer {token_cinema}"},
    )
    assert response.status_code == 200


def test_delete_session():
    response = client.delete(
        f"/cinema/sessions/{session.id}",
        headers={"Authorization": f"Bearer {token_cinema}"},
    )
    assert response.status_code == 204
