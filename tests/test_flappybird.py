from datetime import datetime

from app.main import app
from app.modules.flap import models_flappybird
from tests.commons import TestingSessionLocal, client

user_id = "2e10a287-5e5d-4151-bfa5-bcfffa325433"


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:

        # We add a todo item to be able to try the endpoint
        flappybird_score = models_flappybird.FlappyBirdScore(
            id="0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d",
            user_id=user_id,
            value="25",
            creation_time=datetime.now(),
        )
        db.add(flappybird_score)
        await db.commit()


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass


def test_get_flappybird_score_by_user():
    response = client.get(f"/flappybird/scores/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_get_flappybird_score():
    response = client.get("/flappybird/scores/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_create_flappybird_score():
    response = client.post(
        "/flappybird/scores",
        json={
            "user_id": user_id,
            "value": "25",
        },
    )
    assert response.status_code == 201
    json = response.json()
    assert "value" in json
    assert json["value"] == "25"
