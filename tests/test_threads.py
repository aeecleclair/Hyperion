from typing import TypedDict

from app.main import app
from app.models import models_thread, models_core
from app.utils.types.groups_type import GroupType
from app.utils.types.thread_permissions_types import ThreadPermission
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

UserTest = TypedDict("UserTest", {"user": models_core.CoreUser, "token": str})
users: list[UserTest] = []
test_threads: list[models_thread.Thread] = []


@app.on_event("startup")
async def startup_test():
    async with TestingSessionLocal() as db:
        for i in range(3):
            user = await create_user_with_groups([GroupType.student], db)
            user_token = create_api_access_token(user)
            users.append({"user": user, "token": user_token})
        test_threads.extend(
            [
                models_thread.Thread(name="Test Thread", is_public=True),
                models_thread.Thread(name="Test Thread 2", is_public=False),
            ]
        )
        db.add_all(test_threads)
        await db.commit()
        db.add(
            models_thread.ThreadMember(
                user_id=users[0]["user"].id,
                thread_id=test_threads[1].id,
                permissions=ThreadPermission.ADMINISTRATOR,
            )
        )
        await db.commit()


def test_get_threads():
    response1 = client.get(
        "/threads",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    response2 = client.get(
        "/threads",
        headers={"Authorization": f"Bearer {users[1]['token']}"},
    )
    assert response1.status_code == response2.status_code == 200
    assert len(response1.json()) == 2
    assert len(response2.json()) == 1


def test_create_thread():
    response1 = client.post(
        "/threads",
        json={"name": "Test Thread", "is_public": True},
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response1.status_code == 400
    response2 = client.post(
        "/threads",
        json={"name": "Test Thread (unique)", "is_public": False},
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response2.status_code == 204


def test_add_thread_user():
    response = client.post(
        f"/threads/{test_threads[1].id}/users",
        json={
            "thread_id": test_threads[1].id,
            "user_id": users[1]["user"].id,
            "permissions": 0,
        },
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 204
    response = client.get(
        "/threads",
        headers={"Authorization": f"Bearer {users[1]['token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2
