import datetime
import uuid

from app.main import app
from app.models import models_advert, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

tag: models_advert.Tag | None = None
advert: models_advert.Advert | None = None
advertiser: models_advert.Advertiser | None = None
group_advertiser: models_core.CoreGroup | None = None
user_admin: models_core.CoreUser | None = None
user_advertiser: models_core.CoreUser | None = None
user_simple: models_core.CoreUser | None = None
token_admin: str = ""
token_advertiser: str = ""
token_simple: str = ""


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global user_admin
    async with TestingSessionLocal() as db:
        user_admin = await create_user_with_groups([GroupType.admin], db=db)
        await db.commit()

    global advertiser
    global group_advertiser
    async with TestingSessionLocal() as db:
        group_advertiser = models_core.CoreGroup(
            id=str(uuid.uuid4()),
            name="advertiser",
            description="",
        )
        db.add(group_advertiser)
        advertiser = models_advert.Advertiser(
            id=str(uuid.uuid4()),
            name=group_advertiser.name,
            group_manager_id=group_advertiser.id,
        )
        await db.commit()

    global user_advertiser
    async with TestingSessionLocal() as db:
        user_advertiser = await create_user_with_groups([group_advertiser.id], db=db)
        await db.commit()

    global token_advertiser
    token_advertiser = create_api_access_token(user_advertiser)

    global user_simple
    async with TestingSessionLocal() as db:
        user_simple = await create_user_with_groups([GroupType.student], db=db)
        await db.commit()

    global token_simple
    token_simple = create_api_access_token(user_simple)

    global advert
    global tag
    async with TestingSessionLocal() as db:
        advert = models_advert.Advert(
            id=str(uuid.uuid4()),
            advertiser_id=advertiser.id,
            title="Advert",
            content="Example of advert",
            date=datetime.datetime.now(),
        )

        tag = models_advert.Tag(id=str(uuid.uuid4()), name="Tag", couleur="Couleur")

        adverts_tags_link = models_advert.AdvertsTagsLink(
            id=str(uuid.uuid4()), advert_id=advert.id, tag_id=tag.id
        )

        db.add(advert)
        db.add(tag)
        db.add(adverts_tags_link)
        await db.commit()


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


def test_post_advert():
    response = client.post(
        "/advert/adverts",
        json={
            "title": "Advert2",
            "content": "2nd example of advert",
            "advertiser_id": advertiser.id,
            "co_advertisers_id": [],
            "tags": ["Tag"],
        },
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 201


def test_edit_advert():
    response = client.patch(
        f"/advert/adverts/{advert.id}",
        json={"name": "AdvertEdited"},
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 200


def test_delete_session():
    response = client.delete(
        f"/advert/adverts/{advert.id}",
        headers={"Authorization": f"Bearer {token_advertiser}"},
    )
    assert response.status_code == 204
