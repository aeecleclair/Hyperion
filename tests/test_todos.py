from datetime import datetime

from app.main import app
from app.models import models_todos
from tests.commons import TestingSessionLocal, client

user_id = "2e10a287-5e5d-4151-bfa5-bcfffa325433"


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:

        # We add a todo item to be able to try the endpoint
        todos_item = models_todos.TodosItem(
            todo_id="0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d",
            user_id=user_id,
            name="Creer un module",
            deadline=datetime.now(),
            creation_time=datetime.now(),
        )
        db.add(todos_item)
        await db.commit()


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass


def test_get_todos():
    response = client.get(f"/todos/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_create_todo():
    response = client.post(
        "/todos/",
        json={
            "user_id": user_id,
            "name": "New todo item",
            # "deadline": 1662012000,
        },
    )
    assert response.status_code == 201
    json = response.json()
    assert "name" in json
    assert json["name"] == "New todo item"
