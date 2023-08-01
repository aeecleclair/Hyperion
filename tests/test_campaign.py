import uuid

import pytest_asyncio

from app.models import models_campaign, models_core
from app.utils.types.campaign_type import ListType
from app.utils.types.groups_type import GroupType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import event_loop  # noqa
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

caa_user: models_core.CoreUser | None = None
ae_user: models_core.CoreUser | None = None

section: models_campaign.Sections | None = None
list: models_campaign.Lists | None = None

section2id: str = ""
list2id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global caa_user, ae_user

    caa_user = await create_user_with_groups([GroupType.CAA, GroupType.AE])
    ae_user = await create_user_with_groups([GroupType.AE])

    global section
    global list
    list_id = str(uuid.uuid4())
    section_id = str(uuid.uuid4())

    section = models_campaign.Sections(
        id=section_id,
        name="BDE",
        description="Bureau Des Eleves",
    )
    await add_object_to_db(section)

    list = models_campaign.Lists(
        id=list_id,
        name="Liste 1",
        description="une liste",
        section_id=section_id,
        type=ListType.serio,
        members=[
            models_campaign.ListMemberships(
                user_id=caa_user.id, list_id=list_id, role="Prez"
            ),
            models_campaign.ListMemberships(
                user_id=ae_user.id, list_id=list_id, role="SG"
            ),
        ],
        program="Mon program",
    )
    await add_object_to_db(list)


def test_get_sections():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/sections",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200


def test_add_sections():
    token = create_api_access_token(caa_user)
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


def test_delete_section():
    token = create_api_access_token(caa_user)
    response = client.delete(
        f"/campaign/sections/{section2id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_lists():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_add_list():
    token = create_api_access_token(caa_user)
    response = client.post(
        "/campaign/lists",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Mr Reboot",
            "description": "Probablement la meilleure liste disponible",
            "type": "Serio",
            "section_id": section.id,
            "members": [{"user_id": caa_user.id, "role": "Prez"}],
            "program": "Contacter la DSI",
        },
    )
    assert response.status_code == 201
    global list2id
    list2id = response.json()["id"]


def test_delete_list():
    token = create_api_access_token(caa_user)
    response = client.delete(
        f"/campaign/lists/{list2id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_update_list():
    token = create_api_access_token(caa_user)
    response = client.patch(
        f"/campaign/lists/{list.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Liste 1 Update",
            "members": [{"user_id": caa_user.id, "role": "Prez"}],
        },
    )
    assert response.status_code == 204


def test_create_campaigns_logo():
    token = create_api_access_token(caa_user)

    with open("assets/images/default_campaigns_logo.png", "rb") as image:
        response = client.post(
            f"/campaign/lists/{list.id}/logo",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_vote_if_not_opened():
    # An user should be able to vote if the status is not opened
    token = create_api_access_token(ae_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 400


def test_open_vote():
    token = create_api_access_token(caa_user)
    response = client.post(
        "/campaign/status/open",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 204


def test_read_campaigns_logo():
    token = create_api_access_token(ae_user)

    response = client.get(
        f"/campaign/lists/{list.id}/logo",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_vote_if_opened():
    # As the status is now opened, the user should be able to vote
    token = create_api_access_token(ae_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 204


def test_vote_a_second_time_for_the_same_section():
    # An user should not be able to vote twice for the same section
    token = create_api_access_token(ae_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": list.id},
    )
    assert response.status_code == 400


def test_get_sections_already_voted():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_stats_for_section():
    token = create_api_access_token(caa_user)
    response = client.get(
        f"/campaign/stats/{section.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_results_while_open():
    # As the status is open, nobody should be able to access results
    token = create_api_access_token(caa_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_close_vote():
    token = create_api_access_token(caa_user)
    response = client.post(
        "/campaign/status/close", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_count_vote():
    token = create_api_access_token(caa_user)
    response = client.post(
        "/campaign/status/counting", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_get_results_while_counting():
    # As the status is counting, only CAA user should be able to access results
    token = create_api_access_token(caa_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_publish_vote():
    token = create_api_access_token(caa_user)
    response = client.post(
        "/campaign/status/published", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204


def test_get_results_while_published():
    token = create_api_access_token(ae_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_reset_votes():
    token = create_api_access_token(caa_user)
    response = client.post(
        "/campaign/status/reset",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
