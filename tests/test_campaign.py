import uuid
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.core_endpoints import models_core
from app.core.groups.groups_type import GroupType
from app.modules.campaign import models_campaign
from app.modules.campaign.types_campaign import ListType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

CAA_user: models_core.CoreUser
AE_user: models_core.CoreUser

section: models_campaign.Sections
campaign_list: models_campaign.Lists

section2id: str
list2id: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global CAA_user, AE_user

    CAA_user = await create_user_with_groups(
        [GroupType.CAA, GroupType.AE],
    )
    AE_user = await create_user_with_groups([GroupType.AE])

    global section
    global campaign_list
    list_id = str(uuid.uuid4())
    section_id = str(uuid.uuid4())

    section = models_campaign.Sections(
        id=section_id,
        name="BDE",
        description="Bureau Des Eleves",
    )
    await add_object_to_db(section)

    campaign_list = models_campaign.Lists(
        id=list_id,
        name="Liste 1",
        description="une liste",
        section_id=section_id,
        type=ListType.serio,
        members=[
            models_campaign.ListMemberships(
                user_id=CAA_user.id,
                list_id=list_id,
                role="Prez",
            ),
            models_campaign.ListMemberships(
                user_id=AE_user.id,
                list_id=list_id,
                role="SG",
            ),
        ],
        program="Mon program",
    )
    await add_object_to_db(campaign_list)

    voters_AE = models_campaign.VoterGroups(
        group_id=GroupType.AE,
    )
    await add_object_to_db(voters_AE)
    voters_CAA = models_campaign.VoterGroups(
        group_id=GroupType.CAA,
    )
    await add_object_to_db(voters_CAA)


def test_get_sections(client: TestClient) -> None:
    token = create_api_access_token(AE_user)
    response = client.get(
        "/campaign/sections",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200


def test_add_sections(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
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


def test_delete_section(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.delete(
        f"/campaign/sections/{section2id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_voters(client: TestClient) -> None:
    token = create_api_access_token(AE_user)
    response = client.get(
        "/campaign/voters",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200


def test_delete_voter_by_group_id(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.delete(
        f"/campaign/voters/{GroupType.CAA}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_voters(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.delete(
        "/campaign/voters",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_add_voters(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/voters",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "group_id": GroupType.AE,
        },
    )
    assert response.status_code == 201


def test_get_lists(client: TestClient) -> None:
    token = create_api_access_token(AE_user)
    response = client.get(
        "/campaign/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_add_list(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/lists",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Mr Reboot",
            "description": "Probablement la meilleure liste disponible",
            "type": "Serio",
            "section_id": section.id,
            "members": [{"user_id": CAA_user.id, "role": "Prez"}],
            "program": "Contacter la DSI",
        },
    )
    assert response.status_code == 201
    global list2id
    list2id = response.json()["id"]


def test_delete_list(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.delete(
        f"/campaign/lists/{list2id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_update_list(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.patch(
        f"/campaign/lists/{campaign_list.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Liste 1 Update",
            "members": [{"user_id": CAA_user.id, "role": "Prez"}],
        },
    )
    assert response.status_code == 204


def test_create_campaigns_logo(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)

    with Path("assets/images/default_campaigns_logo.png").open("rb") as image:
        response = client.post(
            f"/campaign/lists/{campaign_list.id}/logo",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_vote_if_not_opened(client: TestClient) -> None:
    # An user should be able to vote if the status is not opened
    token = create_api_access_token(AE_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": campaign_list.id},
    )
    assert response.status_code == 400


def test_open_vote(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/status/open",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 204


def test_read_campaigns_logo(client: TestClient) -> None:
    token = create_api_access_token(AE_user)

    response = client.get(
        f"/campaign/lists/{campaign_list.id}/logo",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_vote_if_opened(client: TestClient) -> None:
    # As the status is now opened, the user should be able to vote
    token = create_api_access_token(AE_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": campaign_list.id},
    )
    assert response.status_code == 204


def test_vote_a_second_time_for_the_same_section(client: TestClient) -> None:
    # An user should not be able to vote twice for the same section
    token = create_api_access_token(AE_user)
    response = client.post(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
        json={"list_id": campaign_list.id},
    )
    assert response.status_code == 400


def test_get_sections_already_voted(client: TestClient) -> None:
    token = create_api_access_token(AE_user)
    response = client.get(
        "/campaign/votes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_stats_for_section(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.get(
        f"/campaign/stats/{section.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_results_while_open(client: TestClient) -> None:
    # As the status is open, nobody should be able to access results
    token = create_api_access_token(CAA_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_close_vote(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/status/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_count_vote(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/status/counting",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_results_while_counting(client: TestClient) -> None:
    # As the status is counting, only CAA user should be able to access results
    token = create_api_access_token(CAA_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_publish_vote(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/status/published",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_results_while_published(client: TestClient) -> None:
    token = create_api_access_token(AE_user)
    response = client.get(
        "/campaign/results",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_reset_votes(client: TestClient) -> None:
    token = create_api_access_token(CAA_user)
    response = client.post(
        "/campaign/status/reset",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
