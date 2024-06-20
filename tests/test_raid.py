import datetime
import uuid

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.booking import models_booking
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

raid_admin_user: models_core.CoreUser
simple_user: models_core.CoreUser

token_raid_admin: str
token_simple: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global raid_admin_user, token_raid_admin
    raid_admin_user = await create_user_with_groups([GroupType.raid_admin])
    token_raid_admin = create_api_access_token(raid_admin_user)

    global simple_user, token_simple
    simple_user = await create_user_with_groups([GroupType.student])
    token_simple = create_api_access_token(simple_user)


def test_create_user_and_team() -> None:
    response = client.post(
        "/raid/participants",
        json={
            "firstname": "Fabristpp",
            "name": "eclair",
            "birthday": "2001-01-01",
            "phone": "0606060606",
            "email": "email@email.fr",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201

    response = client.post(
        "/raid/teams",
        json={
            "name": "MyTeam",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "MyTeam"
