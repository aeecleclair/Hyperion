import datetime
import uuid

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.sports_results import models_sport_results
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

user_simple: models_core.CoreUser
user_captain: models_core.CoreUser
bds_user: models_core.CoreUser

token_simple: str
token_captain: str
token_bds: str

sport1: models_sport_results.Sport
sport2: models_sport_results.Sport
result1: models_sport_results.Result
result2: models_sport_results.Result

captain: models_sport_results.Captain


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects(client: TestClient) -> None:
    global bds_user
    bds_user = await create_user_with_groups([GroupType.BDS])

    global token_bds
    token_bds = create_api_access_token(bds_user)

    global user_simple
    user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(user_simple)

    global sport1
    sport1 = models_sport_results.Sport(
        id=str(uuid.uuid4()),
        name="volley",
    )
    await add_object_to_db(sport1)

    global sport2
    sport2 = models_sport_results.Sport(
        id=str(uuid.uuid4()),
        name="pétanque",
    )
    await add_object_to_db(sport2)

    global user_captain
    user_captain = await create_user_with_groups([GroupType.student])

    global captain
    captain = models_sport_results.Captain(
        id=str(uuid.uuid4()),
        user_id=user_captain.id,
        sports=[sport1],
    )
    await add_object_to_db(captain)

    global token_captain
    token_captain = create_api_access_token(user_captain)

    global result1
    result1 = models_sport_results.Result(
        id=str(uuid.uuid4()),
        sport_id=sport1.id,
        score1=21,
        score2=2,
        rank=1,
        location="Gymnase ECL",
        match_date=datetime.date(2024, 5, 28),
    )
    await add_object_to_db(result1)

    global result2
    result2 = models_sport_results.Result(
        id=str(uuid.uuid4()),
        sport_id=sport2.id,
        score1=12,
        score2=14,
        rank=2,
        location="Terrain ECL",
        match_date=datetime.date(2024, 4, 27),
    )
    await add_object_to_db(result2)


def test_get_results(client: TestClient) -> None:
    response = client.get(
        "/sport-results/results/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    response_json = response.json()
    assert response.status_code == 200
    assert str(result1.id) in [
        response_result["id"] for response_result in response_json
    ]
    assert str(result2.id) in [
        response_result["id"] for response_result in response_json
    ]


def test_get_results_by_sport_id(client: TestClient) -> None:
    response = client.get(
        f"/sport-results/results/sport/{sport1.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    response_json = response.json()
    assert response.status_code == 200
    assert str(result1.id) in [
        response_result["id"] for response_result in response_json
    ]
    assert str(result2.id) in [
        response_result["id"] for response_result in response_json
    ]


def test_get_result_by_id(client: TestClient) -> None:
    response = client.get(
        f"/sport-results/results/{result1.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    response_json = response.json()
    assert response.status_code == 200
    assert str(result1.id) == response_json["id"]


def test_get_sports(client: TestClient) -> None:
    response = client.get(
        "/sport-results/sports/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    response_json = response.json()
    assert response.status_code == 200
    assert str(sport1.id) in [response_sport["id"] for response_sport in response_json]
    assert str(sport2.id) in [response_sport["id"] for response_sport in response_json]


def test_add_sport(client: TestClient) -> None:
    response = client.post(
        "/sport-results/sport",
        json={
            "name": "badminton",
            "captains": [],
        },
        headers={"Authorization": f"Bearer {token_bds}"},
    )
    assert response.status_code == 201


def test_update_sport(client: TestClient) -> None:
    response = client.patch(
        f"/sport-results/sport/{sport1.id}",
        json={
            "name": "tennis",
        },
        headers={"Authorization": f"Bearer {token_bds}"},
    )
    assert response.status_code == 204


def test_delete_sport(client: TestClient) -> None:
    response = client.delete(
        f"/sport-results/sport/{sport1.id}",
        headers={"Authtorization": f"Bearer {token_bds}"},
    )
    assert response.status_code == 204


def test_add_result(client: TestClient) -> None:
    response = client.post(
        "/sport-results/result",
        json={
            "sport_id": result1.id,
            "score1": result1.score1,
            "score2": result1.score2,
            "rank": result1.rank,
            "location": result1.location,
            "match_date": result1.match_date,
        },
        headers={"Authtorization": f"Bearer {token_captain}"},
    )
    assert response.status_code == 201