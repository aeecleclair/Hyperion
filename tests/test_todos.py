from datetime import date

from app.main import app
from app.models import models_core, models_todos
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

user: models_core.CoreUser | None = None


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global user
    async with TestingSessionLocal() as db:
        # We create an user in the test database
        user = await create_user_with_groups([], db=db)

        # We add a todo item to be able to try the endpoint
        todos_item = models_todos.TodosItem(
            id="0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d",
            user_id=user.id,
            name="Créer un module",
            deadline=date.today(),
            creation=date.today(),
            done=False,
        )
        db.add(todos_item)
        await db.commit()


def test_get_todos():
    token = create_api_access_token(user)

    response = client.get(
        "/todos/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    # There should be at least a todo item in the answer: the one we created in startuptest
    data = response.json()
    assert len(data) > 0


def test_create_todo():
    token = create_api_access_token(user)

    response = client.post(
        "/todos/",
        json={
            "name": "New todo item",
            "deadline": "2021-12-31",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    json = response.json()
    assert "name" in json
    assert json["name"] == "New todo item"


def test_check_todo():
    token = create_api_access_token(user)

    response = client.post(
        "/todos/0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d/check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
