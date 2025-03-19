import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.users import models_users
from app.modules.raid import schemas_raid
from tests.commons import (
    create_api_access_token,
    create_user_with_groups,
)

raid_user: models_users.CoreUser

token_raid: str

temps: schemas_raid.Temps


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global raid_user
    raid_user = await create_user_with_groups([])

    global token_raid
    token_raid = create_api_access_token(raid_user)

    global temps
    temps = schemas_raid.Temps(
        id="1",
        dossard=1,
        date="2025-03-15",
        parcours="Sportif",
        ravito="2",
        status=True,
        last_modification_date="2025-03-15",
    )


def test_create_teamps(client: TestClient) -> None:
    response = client.post(
        "/chrono_raid/temps",
        json={
            "id": "1",
            "dossard": 1,
            "date": "2025-03-15",
            "parcours": "Sportif",
            "ravito": "2",
            "status": True,
            "last_modification_date": "2025-03-15",
        },
        headers={"Authorization": f"Bearer {token_raid}"},
    )
    assert response.status_code == 201


def test_get_temps(client: TestClient) -> None:
    response = client.get(
        "/chrono_raid/temps",
        headers={"Authorization": f"Bearer {token_raid}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["id"] == temps.id
