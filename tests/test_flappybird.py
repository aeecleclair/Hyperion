from datetime import datetime

from app.core.groups.groups_type import GroupType
from app.main import app
from app.modules.flap import models_core, models_flappybird
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

user_id = "2e10a287-5e5d-4151-bfa5-bcfffa325433"
user: models_core.CoreUser | None = None


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global user
    async with TestingSessionLocal() as db:
        # We add a todo item to be able to try the endpoint
        user = await create_user_with_groups([GroupType.student], db=db)

        flappybird_score = models_flappybird.FlappyBirdScore(
            id="0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d",
            user_id=user.id,
            user=user,
            value=25,
            creation_time=datetime.now(),
        )
        db.add(flappybird_score)

        await db.commit()


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with (
        client
    ):  # That syntax trigger the startup events in commons.py and all test files
        pass


def test_create_flappybird_score():
    token = create_api_access_token(user=user)
    response = client.post(
        "/flappybird/scores/me?value=25",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    json = response.json()
    assert "value" in json
    assert json["value"] == 25


def test_get_flappybird_user_score():
    token = create_api_access_token(user=user)
    response = client.get(
        "/flappybird/scores/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_get_flappybird_position_score():
    token = create_api_access_token(user=user)
    response = client.get(
        "/flappybird/scores/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_get_flappybird_score():
    token = create_api_access_token(user=user)
    response = client.get(
        "/flappybird/scores/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
