import pytest_asyncio

from app.models import models_core
from app.utils.types.groups_type import GroupType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import event_loop  # noqa
from tests.commons import client, create_api_access_token, create_user_with_groups

user: models_core.CoreUser

token_admin: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global user
    user = await create_user_with_groups([GroupType.external])

    global user_admin
    user_admin = await create_user_with_groups([GroupType.admin])

    global token_admin
    token_admin = create_api_access_token(user_admin)


def test_disable_external_account():
    global user
    response = client.get(
        "/external/",
        follow_redirects=False,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    response1 = client.get(
        f"/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response1.status_code == 200
    data = response1.json()
    assert not data["enabled"]
