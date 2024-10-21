from datetime import UTC, datetime
from uuid import uuid4

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.modules.flappybird import cruds_flappybird, models_flappybird
from tests.commons import add_object_to_db, create_user_with_groups, send_test_db


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global users
    users = [await create_user_with_groups([GroupType.student]) for i in range(3)]

    global flappybird_leaderboard
    flappybird_leaderboard = [
        models_flappybird.FlappyBirdBestScore(
            id=uuid4(),
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
            id=uuid4(),
            user_id=users[main_user_number].id,
            user=users[main_user_number],
            value=25,
            creation_time=datetime.now(UTC),
        )
        for i in range(3)
    ]


async def test_get_flappbird_score_leaderboard() -> None:
    for best_score in flappybird_leaderboard:
        await add_object_to_db(best_score)

    # db_session = await anext(override_get_db())
    async with send_test_db() as db_session:
        test_return_value = await cruds_flappybird.get_flappybird_score_leaderboard(
            db=db_session,
        )
        assert test_return_value == flappybird_leaderboard


async def test_get_flappybird_personal_best_by_user_id() -> None:
    await add_object_to_db(flappybird_leaderboard[main_user_number])

    async with send_test_db() as db_session:
        test_return_value = (
            await cruds_flappybird.get_flappybird_personal_best_by_user_id(
                db=db_session,
                user_id=users[main_user_number].id,
            )
        )
        assert test_return_value == flappybird_leaderboard[main_user_number]
