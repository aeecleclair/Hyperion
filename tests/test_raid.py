import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.modules.raid import models_raid
from app.core.groups.groups_type import GroupType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

import uuid
import datetime

participant: models_raid.Participant

team: models_raid.Team

raid_admin_user: models_core.CoreUser
simple_user: models_core.CoreUser
simple_user_without_participant: models_core.CoreUser
simple_user_without_team: models_core.CoreUser

token_raid_admin: str
token_simple: str
token_simple_without_participant: str
token_simple_without_team: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global raid_admin_user, token_raid_admin
    raid_admin_user = await create_user_with_groups([GroupType.raid_admin])
    token_raid_admin = create_api_access_token(raid_admin_user)

    global simple_user, token_simple
    simple_user = await create_user_with_groups([GroupType.student])
    token_simple = create_api_access_token(simple_user)

    global simple_user_without_participant, token_simple_without_participant
    simple_user_without_participant = await create_user_with_groups([GroupType.student])
    token_simple_without_participant = create_api_access_token(simple_user_without_participant)

    global simple_user_without_team, token_simple_without_team
    simple_user_without_team = await create_user_with_groups([GroupType.student])
    token_simple_without_team = create_api_access_token(simple_user_without_team)

    global participant
    participant = models_raid.Participant(
        id=simple_user.id,
        firstname="TestFirstname",
        name="TestName",
        birthday=datetime.date(2001, 1, 1),
        phone="0606060606",
        email="test@email.fr",
        t_shirt_size="M",
    )
    await add_object_to_db(participant)

    global team
    team = models_raid.Team(
        id=str(uuid.uuid4()),
        name="TestTeam",
        captain_id=simple_user.id,
    )
    await add_object_to_db(team)

    
    no_team_participant = models_raid.Participant(
        id=simple_user_without_team.id,
        firstname="NoTeam",
        name="NoTeam",
        birthday=datetime.date(2001, 1, 1),
        phone="0606060606",
        email="test@no_team.fr",
    )
    await add_object_to_db(no_team_participant)


def test_get_participant_by_id(client: TestClient):
    response = client.get(
        f"/raid/participants/{simple_user.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == simple_user.id

def test_create_participant(client: TestClient):
    participant_data = {
        "firstname": "New",
        "name": "Participant",
        "birthday": "2000-01-01",
        "phone": "0123456789",
        "email": "new@participant.com"
    }
    response = client.post(
        "/raid/participants",
        json=participant_data,
        headers={"Authorization": f"Bearer {token_simple_without_participant}"},
    )
    assert response.status_code == 201
    assert response.json()["firstname"] == "New"

def test_update_participant(client: TestClient):
    update_data = {"firstname": "Updated"}
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204

def test_create_team(client: TestClient):
    team_data = {"name": "New Team"}
    response = client.post(
        "/raid/teams",
        json=team_data,
        headers={"Authorization": f"Bearer {token_simple_without_team}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "New Team"

def test_get_team_by_participant_id(client: TestClient):
    response = client.get(
        f"/raid/participants/{simple_user.id}/team",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert "id" in response.json()

def test_get_all_teams(client: TestClient):
    response = client.get(
        "/raid/teams",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_team_by_id(client: TestClient):
    response = client.get(
        f"/raid/teams/{team.id}",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == team.id

def test_update_team(client: TestClient):
    update_data = {"name": "Updated Team"}
    response = client.patch(
        f"/raid/teams/{team.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204

def test_delete_team(client: TestClient):
    response = client.delete(
        f"/raid/teams/{team.id}",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204

def test_upload_document(client: TestClient):
    file_content = b"test document content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    response = client.post(
        "/raid/document",
        files=files,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    assert "id" in response.json()

## Required google access
# def test_read_document(client: TestClient):
#     # Upload a document first
#     file_content = b"test document content"
#     files = {"file": ("test.pdf", file_content, "application/pdf")}
#     upload_response = client.post(
#         "/raid/document",
#         files=files,
#         headers={"Authorization": f"Bearer {token_simple}"},
#     )
#     assert upload_response.status_code == 201
#     document_id = upload_response.json()["id"]
#     document_id = "some_document_id"
#     response = client.get(
#         f"/raid/document/{document_id}",
#         headers={"Authorization": f"Bearer {token_simple}"},
#     )
#     assert response.status_code == 200

## requires a document to be added
# def test_validate_document(client: TestClient):
#     document_id = "id_card_id"
#     validation_data = {"validation": "validated"}
#     response = client.post(
#         f"/raid/document/{document_id}/validate",
#         json=validation_data,
#         headers={"Authorization": f"Bearer {token_raid_admin}"},
#     )
#     assert response.status_code == 204

## Requires information to be set
# def test_set_security_file(client: TestClient):
#     security_file_data = {
#         "asthma": True,
#         "emergency_contact_name": "Emergency Contact",
#         "emergency_contact_phone": "0987654321"
#     }
#     response = client.post(
#         f"/raid/security_file/?participant_id={simple_user.id}",
#         json=security_file_data,
#         headers={"Authorization": f"Bearer {token_simple}"},
#     )
#     assert response.status_code == 201

def test_confirm_payment(client: TestClient):
    response = client.post(
        f"/raid/participant/{simple_user.id}/payment",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204

def test_confirm_t_shirt_payment(client: TestClient):
    response = client.post(
        f"/raid/participant/{simple_user.id}/t_shirt_payment",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204

def test_validate_attestation_on_honour(client: TestClient):
    response = client.post(
        f"/raid/participant/{simple_user.id}/honour",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204

def test_create_invite_token(client: TestClient):
    response = client.post(
        f"/raid/teams/{team.id}/invite",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    assert "token" in response.json()

def test_join_team(client: TestClient):
    # Create an invite token first
    create_token_response = client.post(
        f"/raid/teams/{team.id}/invite",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert create_token_response.status_code == 201
    token = create_token_response.json()["token"]

    # Now use the created token to join the team
    response = client.post(
        f"/raid/teams/join/{token}",
        headers={"Authorization": f"Bearer {token_simple_without_team}"},
    )
    assert response.status_code == 204

## Required a team with two members
# def test_kick_team_member(client: TestClient):
#     response = client.post(
#         f"/raid/teams/{team.id}/kick/{simple_user.id}",
#         headers={"Authorization": f"Bearer {token_raid_admin}"},
#     )
#     assert response.status_code == 201

## 
# def test_merge_teams(client: TestClient):
#     # Create two teams for testing
#     team1_id = team.id

#     team2_response = client.post(
#         "/raid/teams",
#         json={"name": "Team 2"},
#         headers={"Authorization": f"Bearer {token_simple_without_team}"},
#     )
#     assert team2_response.status_code == 201
#     team2_id = team2_response.json()["id"]
#     response = client.post(
#         f"/raid/teams/merge?team1_id={team1_id}&team2_id={team2_id}",
#         headers={"Authorization": f"Bearer {token_raid_admin}"},
#     )
#     assert response.status_code == 201

def test_get_raid_information(client: TestClient):
    response = client.get(
        "/raid/information",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200

def test_update_raid_information(client: TestClient):
    raid_info = {
        "raid_start_date": "2023-09-01",
    }
    response = client.patch(
        "/raid/information",
        json=raid_info,
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204

# def test_update_drive_folders(client: TestClient):
#     folder_data = {"parent_folder_id": "some_folder_id"}
#     response = client.patch(
#         "/raid/drive",
#         json=folder_data,
#         headers={"Authorization": f"Bearer {token_raid_admin}"},
#     )
#     assert response.status_code == 204

## Requires to initalize the driver manager
# def test_get_drive_folders(client: TestClient):
#     response = client.get(
#         "/raid/drive",
#         headers={"Authorization": f"Bearer {token_raid_admin}"},
#     )
#     assert response.status_code == 200

def test_get_raid_price(client: TestClient):
    response = client.get(
        "/raid/price",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200

def test_update_raid_price(client: TestClient):
    price_data = {"student_price": 50, "t_shirt_price": 15}
    response = client.patch(
        "/raid/price",
        json=price_data,
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204

# def test_get_payment_url(client: TestClient):
#     response = client.get(
#         "/raid/pay",
#         headers={"Authorization": f"Bearer {token_simple}"},
#     )
#     assert response.status_code == 201
#     assert "url" in response.json()
