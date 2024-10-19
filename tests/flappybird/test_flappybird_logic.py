import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.dependencies import AsyncDBSession
from app.modules.flappybird import (
    logic_flappybird,
    models_flappybird,
    schemas_flappybird,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global users
    users = [await create_user_with_groups([GroupType.student]) for i in range(5)]

    global flappybird_leaderboard
    flappybird_leaderboard = [
        models_flappybird.FlappyBirdBestScore(
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
        models_flappybird.FlappyBirdScore(
            id=uuid.uuid4(),
            user_id=users[main_user_number].id,
            user=users[main_user_number],
            value=25,
            creation_time=datetime.now(UTC),
        )
        for i in range(3)
    ]


@patch("app.modules.flappybird.cruds_flappybird.get_flappybird_score_leaderboard")
async def test_get_flappybird_score_leaderboard(get_flappybird_score_leaderboard_mock):
    get_flappybird_score_leaderboard_mock.return_value = flappybird_leaderboard
    test_return_value = await logic_flappybird.get_flappybird_score_leaderboard(
        AsyncDBSession(),
    )
    assert test_return_value == flappybird_leaderboard


@patch("app.modules.flappybird.cruds_flappybird.get_flappybird_score_position")
@patch(
    "app.modules.flappybird.cruds_flappybird.get_flappybird_personal_best_by_user_id"
)
async def test_get_current_user_flappbird_personal_best(
    get_flappbird_personal_best_by_user_id_mock, get_flappybird_score_position_mock
):
    """[WARNING] Patch functions are in the inverse way"""
    best_score = flappybird_leaderboard[main_user_number]
    position = 0
    get_flappybird_score_position_mock.return_value = position
    get_flappbird_personal_best_by_user_id_mock.return_value = best_score
    expected_return_value = schemas_flappybird.FlappyBirdScoreCompleteFeedBack(
        value=best_score.value,
        user=best_score.user,
        creation_time=best_score.creation_time,
        position=position,
    )
    test_return_value = (
        await logic_flappybird.get_current_user_flappybird_personnal_best(
            user=users[main_user_number],
            db=AsyncDBSession(),
        )
    )
    assert test_return_value == expected_return_value
