from datetime import UTC, datetime
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.modules.flappybird import cruds_flappybird, models_flappybird
from app.types.sqlalchemy import Base
from tests.commons import add_object_to_db, create_user_with_groups, send_test_db


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global users
    users = [await create_user_with_groups([GroupType.student]) for i in range(5)]

    global flappybird_best_scores
    flappybird_best_scores = [
        models_flappybird.FlappyBirdBestScore(
            id=uuid4(),
            user_id=users[i].id,
            user=users[i],
            value=(len(users) + 1 - i),
            creation_time=datetime.now(UTC),
        )
        for i in range(len(users))
    ]

    global flappybird_scores
    flappybird_scores = [
        models_flappybird.FlappyBirdScore(
            id=uuid4(),
            user_id=users[0].id,
            user=users[0],
            value=25,
            creation_time=datetime.now(UTC),
        )
        for i in range(3)
    ]


async def test_get_flappbird_score_leaderboard() -> None:
    for best_score in flappybird_best_scores:
        await add_object_to_db(best_score)

    # db_session = await anext(override_get_db())
    async with send_test_db() as db_session:
        tested_value = await cruds_flappybird.get_flappybird_score_leaderboard(
            db=db_session,
        )
        assert [value.to_dict() for value in tested_value] == [
            best_score.to_dict() for best_score in flappybird_best_scores
        ]
