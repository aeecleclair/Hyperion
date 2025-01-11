"""
* [ ] All crud operations on meme
    * [ ] Ajout de n memes avec les valeurs bien choisies pour avoir les sort par plusieurs users
    * [ ] Delete de 1 meme
    * [ ] read d'une page de meme dans tous les sens
* [ ] All crud operations on vote
    * [ ] Vote sur 1 meme par plusieurs user
    * [ ] Changement du vote
    * [ ] Delete du vote
    * [ ] Read d'une page meme avec mes votes
* [ ] All crud operations on ban
    * [ ] Ban d'un user et impact sur ses memes
    * [ ] Unban d'un user et impact sur ses memes
* [ ] Testing edge cases with ban
    * [ ] Call d'une méthode par un user ban
"""

import datetime
import uuid
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.cmm import models_cmm
from app.modules.cmm.types_cmm import MemeStatus
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

cmm_user_1: models_core.CoreUser
cmm_user_2: models_core.CoreUser
cmm_user_to_ban: models_core.CoreUser
cmm_admin: models_core.CoreUser

memes_1: list[models_cmm.Meme]
votes_memes_1: list[models_cmm.Vote]
memes_2: list[models_cmm.Meme]
memes_to_ban: list[models_cmm.Meme]
token_user_1: str
token_user_2: str
token_user_to_ban: str
token_admin: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global cmm_user_1
    cmm_user_1 = await create_user_with_groups([])
    global token_cmm_1
    token_cmm_1 = create_api_access_token(cmm_user_1)

    global cmm_user_2
    cmm_user_2 = await create_user_with_groups([])
    global token_cmm_2
    token_cmm_2 = create_api_access_token(cmm_user_2)

    global cmm_user_to_ban
    cmm_user_to_ban = await create_user_with_groups([])
    global token_user_to_ban
    token_user_to_ban = create_api_access_token(cmm_user_1)

    global cmm_admin
    cmm_admin = await create_user_with_groups([GroupType.admin])
    global token_admin
    token_admin = create_api_access_token(cmm_user_1)

    global memes_1
    memes_1 = [
        models_cmm.Meme(
            id=uuid.uuid4(),
            status=MemeStatus.neutral,
            user_id=cmm_user_1.id,
            creation_time=datetime.datetime(24, i, 23, tzinfo=datetime.UTC),
            vote_score=i,
        )
        for i in range(1, 13)
    ]
    global votes_memes_1
    votes_memes_1 = []
    for i, meme in enumerate(memes_1):
        await add_object_to_db(meme)
        if i % 2 == 0:
            vote = models_cmm.Vote(
                id=uuid.uuid4(),
                user_id=cmm_user_1.id,
                meme_id=meme.id,
                positive=True,
            )
            votes_memes_1.append(vote)
            await add_object_to_db(vote)
        if i % 2 == 1:
            vote2 = models_cmm.Vote(
                id=uuid.uuid4(),
                user_id=cmm_user_2.id,
                meme_id=meme.id,
                positive=True,
            )
            votes_memes_1.append(vote2)
            await add_object_to_db(vote2)

    return
    global memes_2
    memes_2 = [
        models_cmm.Meme(
            id=uuid.uuid4(),
            status=MemeStatus.neutral,
            user_id=cmm_user_1.id,
            creation_time=datetime.datetime(24, i, 23, tzinfo=datetime.UTC),
            vote_score=i,
        )
        for i in range(1, 13)
    ]
    for meme in memes_2:
        await add_object_to_db(meme)
    global memes_to_ban
    memes_to_ban = [
        models_cmm.Meme(
            id=uuid.uuid4(),
            status=MemeStatus.neutral,
            user_id=cmm_user_to_ban.id,
            creation_time=datetime.datetime(24, i, 23, tzinfo=datetime.UTC),
            vote_score=i,
        )
        for i in range(1, 13)
    ]
    for meme in memes_to_ban:
        await add_object_to_db(meme)


def test_get_meme_page(client: TestClient) -> None:
    response = client.get(
        "/cmm/memes/?sort_by=best&n_page=1",
        headers={"Authorization": f"Bearer {token_cmm_2}"},
    )
    print(response)
    print(response.status_code)
    print(response.json())
    assert 2 == 1
