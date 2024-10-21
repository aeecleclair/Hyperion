import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.modules.flappybird import schemas_flappybird
from tests.commons import create_api_access_token, create_user_with_groups

flappybird_leaderboard: list[schemas_flappybird.FlappyBirdScoreInDB]
main_user_number: int
token: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global users
    users = [await create_user_with_groups([GroupType.student]) for i in range(3)]

    global flappybird_leaderboard
    flappybird_leaderboard = [
        schemas_flappybird.FlappyBirdScoreInDB(
            id=uuid.uuid4(),
            user_id=users[i].id,
            user=users[i],
            value=(len(users) + 1 - i),
            creation_time=datetime.now(UTC),
        )
        for i in range(len(users))
    ]

    global main_user_number
    main_user_number = 0

    global flappybird_scores
    flappybird_scores = [
        schemas_flappybird.FlappyBirdScore(
            id=uuid.uuid4(),
            user_id=users[main_user_number].id,
            user=users[main_user_number],
            value=25,
            creation_time=datetime.now(UTC),
        )
        for i in range(3)
    ]

    global token
    token = create_api_access_token(users[main_user_number])


@patch("app.modules.flappybird.logic_flappybird.get_flappybird_score_leaderboard")
def test_get_flappybird_scores(
    get_flappybird_score_leaderboard_mock,
    client: TestClient,
) -> None:
    get_flappybird_score_leaderboard_mock.return_value = flappybird_leaderboard
    response = client.get(
        "/flappybird/scores/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == [
        json.loads(score.model_dump_json()) for score in flappybird_leaderboard
    ]


"""
def test_get_current_user_flappybird_personal_best(client: TestClient) -> None:
    response = client.get(
        "/flappybird/scores/me/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_flappybird_score(client: TestClient) -> None:
    response = client.post(
        "/flappybird/scores",
        json={
            "value": "26",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_update_flappybird_score(client: TestClient):
    response = client.post(
        "/flappybird/scores",
        json={
            "value": "24",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
"""
