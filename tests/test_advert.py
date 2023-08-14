import datetime
import uuid

import pytest_asyncio

from app.models import models_advert, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import event_loop  # noqa
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

# tag: models_advert.Tag | None = None
advert: models_advert.Advert | None = None
advertiser: models_advert.Advertiser | None = None
group_advertiser: models_core.CoreGroup | None = None
user_admin: models_core.CoreUser | None = None
user_advertiser: models_core.CoreUser | None = None
user_simple: models_core.CoreUser | None = None
token_admin: str = ""
token_advertiser: str = ""
token_simple: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global user_admin
    user_admin = await create_user_with_groups([GroupType.admin])

    global token_admin
    token_admin = create_api_access_token(user_admin)

    global advertiser
    global group_advertiser

    # group_advertiser = models_core.CoreGroup(
    #     id=str(uuid.uuid4()),
    #     name="advertiser",
    #     description="",
    # )
    # await add_object_to_db(group_advertiser)

    advertiser = models_advert.Advertiser(
        id=str(uuid.uuid4()),
        name='CAA',
        group_manager_id=GroupType.CAA.value,
    )
    await add_object_to_db(advertiser)

    user_advertiser = await create_user_with_groups([GroupType.CAA])

    global token_advertiser
    token_advertiser = create_api_access_token(user_advertiser)

    global user_simple
    user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(user_simple)

    global advert
    global tag
    advert = models_advert.Advert(
        id=str(uuid.uuid4()),
        advertiser_id=advertiser.id,
        title="Advert",
        content="Example of advert",
        date=datetime.datetime.now(),
        tags="Tag1, Tag2, Tag3",
        coadvertisers=[],
    )

    await add_object_to_db(advert)
    # db.add(tag)
    # db.add(adverts_tags_link)


def test_get_adverts():
    response = client.get(
        "/advert/adverts",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_advert_by_id():
    response = client.get(
        f"/advert/adverts/{advert.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_advert_by_advertisers():
    response = client.get(
        f"/advert/adverts?advertisers={advertiser.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_advert():
    response = client.post(
        "/advert/adverts",
        json={
            "title": "Advert2",
            "content": "2nd example of advert",
            "advertiser_id": advertiser.id,
            "coadvertisers_id": [],
            "tags": "Tag1, Tag2",
        },
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 201


def test_edit_advert():
    response = client.patch(
        f"/advert/adverts/{advert.id}",
        json={"content": "Advert Content Edited"},
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 204


def test_delete_advert():
    response = client.delete(
        f"/advert/adverts/{advert.id}",
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 204


def test_get_advertisers():
    response = client.get(
        "/advert/advertisers",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_my_advertisers():
    response = client.get(
        "/advert/me/advertisers",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_advertiser():
    response = client.post(
        "/advert/advertisers",
        json={"name": "Advert2", "group_manager_id": advertiser.group_manager_id},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_edit_advertiser():
    response = client.patch(
        f"/advert/advertisers/{advertiser.id}",
        json={"name": "AdvertiserEdited"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_advertiser():
    response = client.delete(
        f"/advert/advertisers/{advertiser.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
