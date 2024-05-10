from datetime import UTC, datetime

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.flap import models_flappybird
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)

flappybird_score: models_flappybird.FlappyBirdScore | None = None
user: models_core.CoreUser | None = None
token: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global user
    user = await create_user_with_groups([GroupType.student])

    global user_id
    user_id = "2e10a287-5e5d-4151-bfa5-bcfffa325433"

    global token
    token = create_api_access_token(user=user)

    global flappybird_score
    flappybird_score = models_flappybird.FlappyBirdScore(
        id="0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d",
        user_id=user.id,
        user=user,
        value=25,
        creation_time=datetime.now(UTC),
    )

    await add_object_to_db(flappybird_score)


def test_get_flappybird_score():
    response = client.get(
        "/flappybird/scores/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
