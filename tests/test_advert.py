import datetime
import uuid
from pathlib import Path

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.advert import models_advert
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

advert: models_advert.Advert
advertiser: models_advert.Advertiser
user_admin: models_core.CoreUser
user_advertiser: models_core.CoreUser
user_simple: models_core.CoreUser
token_admin: str = ""
token_advertiser: str = ""
token_simple: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global user_admin
    user_admin = await create_user_with_groups([GroupType.admin])

    global token_admin
    token_admin = create_api_access_token(user_admin)

    global advertiser

    advertiser = models_advert.Advertiser(
        id=str(uuid.uuid4()),
        name="CAA",
        group_manager_id=GroupType.CAA.value,
    )
    await add_object_to_db(advertiser)

    user_advertiser = await create_user_with_groups([GroupType.student, GroupType.CAA])

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
        date=datetime.datetime.now(tz=datetime.UTC),
        tags="Tag1, Tag2, Tag3",
    )

    await add_object_to_db(advert)


def test_get_adverts() -> None:
    response = client.get(
        "/advert/adverts",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_advert_by_id() -> None:
    response = client.get(
        f"/advert/adverts/{advert.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_advert_by_advertisers() -> None:
    response = client.get(
        f"/advert/adverts?advertisers={advertiser.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_advert() -> None:
    response = client.post(
        "/advert/adverts",
        json={
            "title": "Advert2",
            "content": "2nd example of advert",
            "advertiser_id": advertiser.id,
            "tags": "Tag1, Tag2",
        },
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 201


def test_create_picture() -> None:
    with Path("assets/images/default_advert.png").open("rb") as image:
        response = client.post(
            f"/advert/adverts/{advert.id}/picture",
            files={"image": ("advert.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_advertiser}"},
        )

    assert response.status_code == 201


def test_get_picture() -> None:
    response = client.get(
        f"/advert/adverts/{advert.id}/picture",
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )

    assert response.status_code == 200


def test_edit_advert() -> None:
    response = client.patch(
        f"/advert/adverts/{advert.id}",
        json={"content": "Advert Content Edited"},
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 204


def test_delete_advert() -> None:
    response = client.delete(
        f"/advert/adverts/{advert.id}",
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 204


def test_get_advertisers() -> None:
    response = client.get(
        "/advert/advertisers",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_my_advertisers() -> None:
    response = client.get(
        "/advert/me/advertisers",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_advertiser() -> None:
    response = client.post(
        "/advert/advertisers",
        json={"name": "Advert2", "group_manager_id": advertiser.group_manager_id},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_edit_advertiser() -> None:
    response = client.patch(
        f"/advert/advertisers/{advertiser.id}",
        json={"name": "AdvertiserEdited"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_advertiser() -> None:
    response = client.delete(
        f"/advert/advertisers/{advertiser.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
