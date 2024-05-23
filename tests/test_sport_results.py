import uuid

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.sports_results import models_sport_results
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

user_simple: models_core.CoreUser
bds_user: models_core.CoreUser

token_simple: str
token_bds: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global bds_user
    bds_user = await create_user_with_groups([GroupType.BDS])

    global token_bds
    token_bds = create_api_access_token(bds_user)

    global user_simple
    user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(user_simple)
