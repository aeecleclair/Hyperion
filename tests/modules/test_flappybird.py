import uuid
from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.users import models_users
from app.modules.flappybird import models_flappybird
from app.modules.flappybird.endpoints_flappybird import FlappyBirdPermissions
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

admin_group: models_groups.CoreGroup
user: models_users.CoreUser
token: str = ""
admin_user: models_users.CoreUser
admin_token: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_group
    admin_group = await create_groups_with_permissions(
        [FlappyBirdPermissions.manage_flappybird],
        "flappybird_admin",
    )
    global user
    user = await create_user_with_groups(
        [],
    )

    global admin_user
    admin_user = await create_user_with_groups([admin_group.id])

    global token
    token = create_api_access_token(user=user)

    global admin_token
    admin_token = create_api_access_token(user=admin_user)

    flappybird_best_score = models_flappybird.FlappyBirdBestScore(
        id=uuid.uuid4(),
        user_id=user.id,
        value=25,
        creation_time=datetime.now(UTC),
    )

    await add_object_to_db(flappybird_best_score)


def test_get_flappybird_score(client: TestClient) -> None:
    response = client.get(
        "/flappybird/scores/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


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


def test_delete_flappybird_score(client: TestClient):
    response = client.delete(
        f"flappybird/scores/{user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204
