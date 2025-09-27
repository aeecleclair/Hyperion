import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.users import models_users
from app.modules.raid import models_raid, schemas_raid
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

raid_user: models_users.CoreUser

token_raid: str

temps: models_raid.Temps
temps2: models_raid.Temps
remark: models_raid.Remark


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global raid_user
    raid_user = await create_user_with_groups([])

    global token_raid
    token_raid = create_api_access_token(raid_user)

    global temps
    temps = models_raid.Temps(
        id="1",
        dossard=1,
        date="2025-03-15",
        parcours="Sportif",
        ravito="2",
        status=True,
        last_modification_date="2025-03-15",
    )
    await add_object_to_db(temps)

    global temps2
    temps2 = models_raid.Temps(
        id="2",
        dossard=1,
        date="2025-01-15",
        parcours="Sportif",
        ravito="2",
        status=True,
        last_modification_date="2025-01-15",
    )
    await add_object_to_db(temps2)

    global remark
    remark = models_raid.Remark(
        id="3",
        date="2025-01-15",
        ravito="2",
        text="youplali youplala",
    )
    await add_object_to_db(remark)


def get_temps(client: TestClient) -> None:
    response = client.get(
        "/chrono_raid/temps",
        headers={"Authorization": f"Bearer {token_raid}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] not in [temps.id, temps2.id]
    assert response.json()[1]["id"] not in [temps.id, temps2.id]


def get_temps_by_date(client: TestClient) -> None:
    response = client.get(
        "/chrono_raid/temps/2025-02-15",
        headers={"Authorization": f"Bearer {token_raid}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == temps.id


def get_remarks(client: TestClient) -> None:
    response = client.get(
        "/chrono_raid/remarks",
        headers={"Authorization": f"Bearer {token_raid}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == remark.id


def add_remarks(client: TestClient) -> None:
    response = client.post(
        "/chrono_raid/remarks",
        json=[
            {
                "id": "4",
                "date": "2025-01-15",
                "ravito": "2",
                "text": "Tung Tung Tung Sahur",
            },
        ],
        headers={"Authorization": f"Bearer {token_raid}"},
    )
    assert response.status_code == 200
