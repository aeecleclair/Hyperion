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
student_user: models_core.CoreUser | None = None

section: models_campaign.Sections | None = None
list: models_campaign.Lists | None = None


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global admin_user, student_user

    async with TestingSessionLocal() as db:
        admin_user = await create_user_with_groups([GroupType.admin], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

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
                    user_id=admin_user.id, group_id=list_id, role="Prez"
                ),
                models_campaign.ListMemberships(
                    user_id=student_user.id, group_id=list_id, role="SG"
                ),
            ],
        )
        db.add(section)
        db.add(list)
        await db.commit()


def test_get_sections():
    token = create_api_access_token(student_user)
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


def test_get_lists_from_section():
    token = create_api_access_token(student_user)
    response = client.get(
        f"/campaign/sections/{section.id}/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_lists():
    token = create_api_access_token(student_user)
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


def test_vote_if_not_opened():
    token = create_api_access_token(student_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 403


def test_vote_if_opened():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/votes/open", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201

    token = create_api_access_token(student_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 201


def test_delete_list():
    token = create_api_access_token(admin_user)
    response = client.delete(
        f"/campaign/lists/{list.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_section():
    token = create_api_access_token(admin_user)
    response = client.delete(
        f"/campaign/sections/{section.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
