import uuid

from app.main import app
from app.models import models_campaign, models_core
from app.utils.types.campaign_type import ListType
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser | None = None
ae_user: models_core.CoreUser | None = None

section: models_campaign.Sections | None = None
list: models_campaign.Lists | None = None

section2id: str = ""
list2id: str = ""


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global admin_user, ae_user

    async with TestingSessionLocal() as db:
        admin_user = await create_user_with_groups([GroupType.admin], db=db)
        ae_user = await create_user_with_groups([GroupType.AE], db=db)

        await db.commit()

    global section
    global list
    list_id = str(uuid.uuid4())
    section_id = str(uuid.uuid4())
    async with TestingSessionLocal() as db:
        section = models_campaign.Sections(
            id=section_id,
            name="BDE",
            description="Bureau Des Eleves",
        )
        list = models_campaign.Lists(
            id=list_id,
            name="Liste 1",
            description="une liste",
            section_id=section_id,
            type=ListType.serio,
            members=[
                models_campaign.ListMemberships(
                    user_id=admin_user.id, list_id=list_id, role="Prez"
                ),
                models_campaign.ListMemberships(
                    user_id=ae_user.id, list_id=list_id, role="SG"
                ),
            ],
        )
        db.add(section)
        db.add(list)
        await db.commit()


def test_get_sections():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/sections", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_add_sections():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/sections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "ECLAIR",
            "description": "Association Informatique",
        },
    )
    assert response.status_code == 201
    global section2id
    section2id = response.json()["id"]


def test_get_lists():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_add_list():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/lists",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Mr Reboot",
            "description": "Probablement la meilleure liste disponible",
            "type": "Serio",
            "section_id": section.id,
            "members": [{"user_id": admin_user.id, "role": "Prez"}],
        },
    )
    assert response.status_code == 201
    global list2id
    list2id = response.json()["id"]


def test_delete_list():
    token = create_api_access_token(admin_user)
    response = client.delete(
        f"/campaign/lists/{list2id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_section():
    token = create_api_access_token(admin_user)
    response = client.delete(
        f"/campaign/sections/{section2id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_vote_if_not_opened():
    token = create_api_access_token(ae_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 400


def test_open_vote():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/status/open", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_vote_if_opened():
    token = create_api_access_token(ae_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 204


def test_get_section_voted_of_user():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_close_vote():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/status/close", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_counting_vote():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/status/counting", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_get_votes():
    token = create_api_access_token(admin_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_reset_votes():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/status/reset",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
