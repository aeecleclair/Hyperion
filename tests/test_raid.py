import datetime
import json
import shutil
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.raid import coredata_raid, models_raid
from app.modules.raid.models_raid import (
    RaidParticipant,
    RaidTeam,
    SecurityFile,
)
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    Size,
)
from app.modules.raid.utils.utils_raid import calculate_raid_payment
from tests.commons import (
    add_coredata_to_db,
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

participant: models_raid.RaidParticipant

team: models_raid.RaidTeam
validated_team: models_raid.RaidTeam

validated_document: models_raid.Document

raid_admin_user: models_users.CoreUser
simple_user: models_users.CoreUser
simple_user_without_participant: models_users.CoreUser
simple_user_without_team: models_users.CoreUser

validated_team_captain: models_users.CoreUser
validated_team_second: models_users.CoreUser

raid_volunteer_user: models_users.CoreUser

token_raid_admin: str
token_simple: str
token_simple_without_participant: str
token_simple_without_team: str

token_validated_team_captain: str
token_raid_volunteer: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global raid_admin_user, token_raid_admin
    raid_admin_user = await create_user_with_groups([GroupType.raid_admin])
    token_raid_admin = create_api_access_token(raid_admin_user)

    global simple_user, token_simple
    simple_user = await create_user_with_groups(
        [],
    )
    token_simple = create_api_access_token(simple_user)

    global simple_user_without_participant, token_simple_without_participant
    simple_user_without_participant = await create_user_with_groups(
        [],
    )
    token_simple_without_participant = create_api_access_token(
        simple_user_without_participant,
    )

    global simple_user_without_team, token_simple_without_team
    simple_user_without_team = await create_user_with_groups(
        [],
    )
    token_simple_without_team = create_api_access_token(simple_user_without_team)

    global validated_team_captain, token_validated_team_captain
    validated_team_captain = await create_user_with_groups([])
    token_validated_team_captain = create_api_access_token(validated_team_captain)

    global validated_team_second
    validated_team_second = await create_user_with_groups([])

    global raid_volunteer_user, token_raid_volunteer
    raid_volunteer_user = await create_user_with_groups([GroupType.raid_volunteer])
    token_raid_volunteer = create_api_access_token(raid_volunteer_user)

    document = models_raid.Document(
        id="some_document_id",
        name="test.pdf",
        uploaded_at=datetime.datetime.now(tz=datetime.UTC),
        validation=DocumentValidation.pending,
        type=DocumentType.idCard,
    )
    await add_object_to_db(document)

    validated_document = models_raid.Document(
        id="6e9736ab-5ceb-42a8-a252-e8c66696f7b1",
        name="validated.pdf",
        uploaded_at=datetime.datetime.now(tz=datetime.UTC),
        validation=DocumentValidation.accepted,
        type=DocumentType.idCard,
    )

    await add_object_to_db(validated_document)

    global participant
    participant = models_raid.RaidParticipant(
        id=simple_user.id,
        firstname="TestFirstname",
        name="TestName",
        birthday=datetime.date(2001, 1, 1),
        phone="0606060606",
        email="test@email.fr",
        t_shirt_size=Size.M,
        id_card_id=document.id,
    )
    await add_object_to_db(participant)

    global team
    team = models_raid.RaidTeam(
        id=str(uuid.uuid4()),
        name="TestTeam",
        captain_id=simple_user.id,
        difficulty=None,
    )
    await add_object_to_db(team)

    no_team_participant = models_raid.RaidParticipant(
        id=simple_user_without_team.id,
        firstname="NoTeam",
        name="NoTeam",
        birthday=datetime.date(2001, 1, 1),
        phone="0606060606",
        email="test@no_team.fr",
    )
    await add_object_to_db(no_team_participant)

    validated_team_participant_captain = models_raid.RaidParticipant(
        id=validated_team_captain.id,
        firstname="Validated",
        name="Captain",
        address="123 rue de la rue",
        birthday=datetime.date(2001, 1, 1),
        phone="0606060606",
        email="test@validated.fr",
        t_shirt_size=Size.M,
        bike_size=Size.M,
        attestation_on_honour=True,
        situation="centrale",
        payment=True,
        id_card_id=validated_document.id,
        medical_certificate_id=validated_document.id,
        student_card_id=validated_document.id,
        raid_rules_id=validated_document.id,
        parent_authorization_id=validated_document.id,
    )

    await add_object_to_db(validated_team_participant_captain)

    validated_team_participant_second = models_raid.RaidParticipant(
        id=validated_team_second.id,
        firstname="Validated",
        name="Second",
        address="123 rue de la rue",
        birthday=datetime.date(2001, 1, 1),
        phone="0606060606",
        email="test2@validated.fr",
        t_shirt_size=Size.M,
        bike_size=Size.M,
        attestation_on_honour=True,
        situation="centrale",
        payment=True,
        id_card_id=validated_document.id,
        medical_certificate_id=validated_document.id,
        student_card_id=validated_document.id,
        raid_rules_id=validated_document.id,
        parent_authorization_id=validated_document.id,
    )

    await add_object_to_db(validated_team_participant_second)

    global validated_team
    validated_team = models_raid.RaidTeam(
        id=str(uuid.uuid4()),
        name="ValidatedTeam",
        difficulty=Difficulty.sports,
        meeting_place=MeetingPlace.centrale,
        captain_id=validated_team_captain.id,
        second_id=validated_team_second.id,
        file_id=str(uuid.uuid4()),
    )

    await add_object_to_db(validated_team)

    Path("data/raid/").mkdir(parents=True, exist_ok=True)
    default_asset = "assets/pdf/default_PDF.pdf"
    expected_files = [
        "-1_ValidatedTeam_Captain_Validated.pdf",
        "-1_New Team_NoTeam_NoTeam.pdf",
    ]
    for path in expected_files:
        shutil.copyfile(
            default_asset,
            "data/raid/" + path,
        )

    await add_coredata_to_db(
        coredata_raid.RaidPrice(
            student_price=50,
            t_shirt_price=15,
            external_price=90,
        ),
    )


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
        "email": "new@participant.com",
    }
    response = client.post(
        "/raid/participants",
        json=participant_data,
        headers={"Authorization": f"Bearer {token_simple_without_participant}"},
    )
    assert response.status_code == 201
    assert response.json()["firstname"] == "New"


def test_confirm_payment(client: TestClient):
    response = client.post(
        f"/raid/participant/{simple_user.id}/payment",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204


# Failing in batch, passing alone
def test_confirm_t_shirt_payment(client: TestClient):
    response = client.post(
        f"/raid/participant/{simple_user.id}/t_shirt_payment",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204


def test_update_participant_success(client: TestClient):
    update_data = {
        "firstname": "UpdatedFirst",
        "name": "UpdatedLast",
        "birthday": "1995-01-01",
        "phone": "9876543210",
        "email": "updated@example.com",
        "t_shirt_size": "L",
    }
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204


def test_update_participant_not_a_participant(client: TestClient):
    update_data = {"firstname": "UpdatedFirst"}
    response = client.patch(
        f"/raid/participants/{simple_user_without_participant.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple_without_participant}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You are not the participant."


def test_update_participant_not_same_team(client: TestClient):
    update_data = {"firstname": "UpdatedFirst"}
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple_without_team}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You are not the participant."


def test_update_participant_change_tshirt_size_before_payment(client: TestClient):
    update_data = {"t_shirt_size": "XL"}
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204


def test_update_participant_change_tshirt_size_after_payment(client: TestClient):
    update_data = {"t_shirt_size": "S"}
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204


def test_update_participant_invalid_document_id(client: TestClient):
    update_data = {"id_card_id": "invalid_id"}
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document id_card not found."


def test_update_participant_invalid_security_file_id(client: TestClient):
    update_data = {"security_file_id": "invalid_id"}
    response = client.patch(
        f"/raid/participants/{simple_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Security_file not found."


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


def test_set_team_number(client: TestClient):
    update_data = {"name": "Updated Validated Team"}
    response = client.patch(
        f"/raid/teams/{validated_team.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_validated_team_captain}"},
    )
    assert response.status_code == 204


def test_upload_document(client: TestClient):
    file_content = b"test document content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    response = client.post(
        "/raid/document/idCard",
        files=files,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    assert "id" in response.json()


def test_read_document_not_found(client: TestClient):
    document_id = "non_existent_document_id"
    response = client.get(
        f"/raid/document/{document_id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_read_document_participant_not_found(client: TestClient):
    # Create a test document without associating it with a participant
    test_file_content = b"orphan document content"
    files = {"file": ("orphan.pdf", test_file_content, "application/pdf")}
    upload_response = client.post(
        "/raid/document/idCard",
        files=files,
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    # Manually remove the participant association (this would typically be done in the database)
    # For the purpose of this test, we're simulating a scenario where the document exists but has no associated participant

    # Now try to read the document as a regular user
    response = client.get(
        f"/raid/document/{document_id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant owning the document not found."


# requires a document to be added
def test_validate_document(client: TestClient):
    document_id = "some_document_id"
    response = client.post(
        f"/raid/document/{document_id}/validate?validation=accepted",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204


def test_set_security_file_success(client: TestClient):
    security_file_data = {
        "asthma": True,
    }
    response = client.post(
        f"/raid/security_file/?participant_id={simple_user.id}",
        json=security_file_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    assert "id" in response.json()


def test_set_security_file_not_in_same_team(client: TestClient):
    security_file_data = {
        "asthma": False,
        "emergency_contact_name": "Another Contact",
        "emergency_contact_phone": "1234567890",
    }
    response = client.post(
        f"/raid/security_file/?participant_id={simple_user_without_team.id}",
        json=security_file_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You are not the participant."


def test_set_security_file_participant_not_exist(client: TestClient):
    security_file_data = {
        "asthma": True,
        "emergency_contact_name": "Non-existent Contact",
        "emergency_contact_phone": "9876543210",
    }
    non_existent_id = "non_existent_id"
    response = client.post(
        f"/raid/security_file/?participant_id={non_existent_id}",
        json=security_file_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You are not the participant."


def test_set_security_file_update_existing(client: TestClient):
    # First, create an initial security file
    initial_data = {
        "asthma": False,
        "emergency_contact_name": "Initial Contact",
        "emergency_contact_phone": "1111111111",
    }
    initial_response = client.post(
        f"/raid/security_file/?participant_id={simple_user.id}",
        json=initial_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert initial_response.status_code == 201

    # Now, update the security file
    updated_data = {
        "asthma": True,
        "emergency_contact_name": "Updated Contact",
        "emergency_contact_phone": "2222222222",
    }
    update_response = client.post(
        f"/raid/security_file/?participant_id={simple_user.id}",
        json=updated_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert update_response.status_code == 201
    assert update_response.json()["id"] != initial_response.json()["id"]


def test_validate_attestation_on_honour(client: TestClient):
    response = client.post(
        f"/raid/participant/{simple_user.id}/honour",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204


# Failing in batch, passing alone
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


def test_kick_team_member(client: TestClient):
    response = client.post(
        f"/raid/teams/{team.id}/kick/{simple_user_without_team.id}",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 201


# Failing in batch, passing alone
def test_create_invite_token(client: TestClient):
    response = client.post(
        f"/raid/teams/{team.id}/invite",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    assert "token" in response.json()


# Fail due to pdf writing error
def test_merge_teams(client: TestClient):
    # Create two teams for testing
    team1_id = team.id

    team2_response = client.post(
        "/raid/teams",
        json={"name": "Team 2"},
        headers={"Authorization": f"Bearer {token_simple_without_participant}"},
    )
    assert team2_response.status_code == 201
    team2_id = team2_response.json()["id"]
    response = client.post(
        f"/raid/teams/merge?team1_id={team1_id}&team2_id={team2_id}",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 201


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


def test_get_raid_price(client: TestClient):
    response = client.get(
        "/raid/price",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_update_raid_price(client: TestClient):
    price_data = {"student_price": 50, "t_shirt_price": 15, "external_price": 90}
    response = client.patch(
        "/raid/price",
        json=price_data,
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204


def test_delete_team(client: TestClient):
    response = client.delete(
        f"/raid/teams/{team.id}",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204


## Test for pdf writer


@pytest.fixture
def mock_team():
    return Mock(
        spec=RaidTeam,
        name="Test Team",
        number=1,
        captain=Mock(
            spec=RaidParticipant,
            name="Doe",
            firstname="John",
            birthday=datetime.datetime(1990, 1, 1, tzinfo=datetime.UTC),
            phone="0606060606",
            email="test@email.fr",
            id=str(uuid.uuid4()),
            bike_size=None,
            t_shirt_size=None,
            situation=None,
            validation_progress=0.1,
            payment=False,
            t_shirt_payment=False,
            number_of_document=1,
            number_of_validated_document=0,
            address=None,
            other_school=None,
            company=None,
            diet=None,
            id_card=None,
            medical_certificate=None,
            security_file=None,
            student_card=None,
            raid_rules=None,
            parent_authorization=None,
            attestation_on_honour=False,
            is_minor=False,
        ),
        validation_progress=10,
    )


@pytest.fixture
def mock_security_file():
    return Mock(spec=SecurityFile, allergy="None", asthma=False)


@pytest.fixture
def mock_participant():
    return Mock(
        spec=RaidParticipant,
        name="Doe",
        firstname="John",
        birthday=datetime.datetime(1990, 1, 1, tzinfo=datetime.UTC),
        phone="0606060606",
        email="test@email.fr",
        id=str(uuid.uuid4()),
        bike_size=None,
        t_shirt_size=None,
        situation=None,
        validation_progress=0.1,
        payment=False,
        t_shirt_payment=False,
        number_of_document=1,
        number_of_validated_document=0,
        address=None,
        other_school=None,
        company=None,
        diet=None,
        id_card=None,
        medical_certificate=None,
        student_card=None,
        raid_rules=None,
        parent_authorization=None,
        attestation_on_honour=False,
        is_minor=False,
        security_file=Mock(spec=SecurityFile, allergy="None", asthma=False),
    )


async def test_set_team_number_utility_empty_database(
    mocker: MockerFixture,
):
    """Test the set_team_number utility with an empty database (no existing teams)"""
    # Create mock objects
    mock_db = mocker.AsyncMock()
    mock_team = mocker.Mock(
        spec=RaidTeam,
        id=str(uuid.uuid4()),
        difficulty=Difficulty.sports,
    )

    # Mock the get_number_of_team_by_difficulty function to return 0
    mocker.patch(
        "app.modules.raid.cruds_raid.get_number_of_team_by_difficulty",
        return_value=0,
    )

    # Mock the update_team function
    mock_update_team = mocker.patch("app.modules.raid.cruds_raid.update_team")

    # Call the function
    from app.modules.raid.utils.utils_raid import set_team_number

    await set_team_number(mock_team, mock_db)

    # Assert update_team was called with correct parameters
    mock_update_team.assert_called_once()
    args, kwargs = mock_update_team.call_args
    assert args[0] == mock_team.id
    assert args[1].number == 101  # 100 (sports separator) + 1


async def test_set_team_number_utility_existing_teams(
    mocker: MockerFixture,
):
    """Test the set_team_number utility with existing teams"""
    # Create mock objects
    mock_db = mocker.AsyncMock()
    mock_team = mocker.Mock(
        spec=RaidTeam,
        id=str(uuid.uuid4()),
        difficulty=Difficulty.expert,
    )

    # Mock the get_number_of_team_by_difficulty function to return existing team numbers
    mocker.patch(
        "app.modules.raid.cruds_raid.get_number_of_team_by_difficulty",
        return_value=220,
    )

    # Mock the update_team function
    mock_update_team = mocker.patch("app.modules.raid.cruds_raid.update_team")

    # Call the function
    from app.modules.raid.utils.utils_raid import set_team_number

    await set_team_number(mock_team, mock_db)

    # Assert update_team was called with correct parameters
    mock_update_team.assert_called_once()
    args, kwargs = mock_update_team.call_args
    assert args[0] == mock_team.id
    assert args[1].number == 221  # 220 + 1


async def test_set_team_number_utility_no_difficulty(
    mocker: MockerFixture,
):
    """Test the set_team_number utility with a team without difficulty"""
    # Create mock objects
    mock_db = mocker.AsyncMock()
    mock_team = mocker.Mock(
        spec=RaidTeam,
        id=str(uuid.uuid4()),
        difficulty=None,
    )

    # Mock the update_team function
    mock_update_team = mocker.patch("app.modules.raid.cruds_raid.update_team")

    # Call the function
    from app.modules.raid.utils.utils_raid import set_team_number

    await set_team_number(mock_team, mock_db)

    # Assert update_team was not called
    mock_update_team.assert_not_called()


async def test_set_team_number_utility_discovery_difficulty(
    mocker: MockerFixture,
):
    """Test the set_team_number utility with discovery difficulty"""
    # Create mock objects
    mock_db = mocker.AsyncMock()
    mock_team = mocker.Mock(
        spec=RaidTeam,
        id=str(uuid.uuid4()),
        difficulty=Difficulty.discovery,
    )

    # Mock the get_number_of_team_by_difficulty function
    mocker.patch(
        "app.modules.raid.cruds_raid.get_number_of_team_by_difficulty",
        return_value=5,
    )
    # Mock the update_team function
    mock_update_team = mocker.patch("app.modules.raid.cruds_raid.update_team")

    # Call the function
    from app.modules.raid.utils.utils_raid import set_team_number

    await set_team_number(mock_team, mock_db)

    # Assert update_team was called with correct parameters
    mock_update_team.assert_called_once()
    args, kwargs = mock_update_team.call_args
    assert args[0] == mock_team.id
    assert args[1].number == 6  # discovery (0) + 5 + 1


@pytest.mark.parametrize(
    ("participant_kwargs", "expected_price"),
    [
        # Student price only
        (
            {
                "payment": False,
                "t_shirt_size": None,
                "t_shirt_payment": False,
                "situation": "centrale",
                "student_card_id": str(uuid.uuid4()),
            },
            50,
        ),
        # Student price only
        (
            {
                "payment": False,
                "t_shirt_size": None,
                "t_shirt_payment": False,
                "situation": "otherschool : Some School",
                "student_card_id": str(uuid.uuid4()),
            },
            50,
        ),
        # Student price only but without student card
        (
            {
                "payment": False,
                "t_shirt_size": None,
                "t_shirt_payment": False,
                "situation": "centrale",
                "student_card_id": None,
            },
            90,
        ),
        # Student price only but without student card
        (
            {
                "payment": False,
                "t_shirt_size": None,
                "t_shirt_payment": False,
                "situation": "otherschool : Some School",
                "student_card_id": None,
            },
            90,
        ),
        # External price only
        (
            {
                "payment": False,
                "t_shirt_size": None,
                "t_shirt_payment": False,
                "situation": "other",
                "student_card_id": None,
            },
            90,
        ),
        # Student price + T-shirt
        (
            {
                "payment": False,
                "t_shirt_size": Size.L,
                "t_shirt_payment": False,
                "situation": "centrale",
                "student_card_id": str(uuid.uuid4()),
            },
            65,
        ),
        # External price + T-shirt
        (
            {
                "payment": False,
                "t_shirt_size": Size.L,
                "t_shirt_payment": False,
                "situation": "other",
                "student_card_id": None,
            },
            105,
        ),
        # Already paid, no T-shirt
        (
            {
                "payment": True,
                "t_shirt_size": None,
                "t_shirt_payment": False,
                "situation": "centrale",
                "student_card_id": str(uuid.uuid4()),
            },
            0,
        ),
        # Already paid, T-shirt not paid
        (
            {
                "payment": True,
                "t_shirt_size": Size.L,
                "t_shirt_payment": False,
                "situation": "centrale",
                "student_card_id": str(uuid.uuid4()),
            },
            15,
        ),
        # Already paid, T-shirt already paid
        (
            {
                "payment": True,
                "t_shirt_size": Size.L,
                "t_shirt_payment": True,
                "situation": "centrale",
                "student_card_id": str(uuid.uuid4()),
            },
            0,
        ),
        # No student card, T-shirt already paid
        (
            {
                "payment": True,
                "t_shirt_size": Size.L,
                "t_shirt_payment": True,
                "situation": "otherschool : Some School",
                "student_card_id": str(uuid.uuid4()),
            },
            0,
        ),
    ],
)
def test_calculate_raid_payment_price_only(participant_kwargs, expected_price):
    raid_prices = coredata_raid.RaidPrice(
        student_price=50,
        t_shirt_price=15,
        external_price=90,
    )
    participant = RaidParticipant(
        id=str(uuid.uuid4()),
        name="Name",
        firstname="Firstname",
        birthday=datetime.date(2000, 1, 1),
        phone="0123456789",
        email="name@example.com",
        payment=participant_kwargs["payment"],
        t_shirt_size=participant_kwargs["t_shirt_size"],
        t_shirt_payment=participant_kwargs["t_shirt_payment"],
        situation=participant_kwargs["situation"],
        student_card_id=participant_kwargs["student_card_id"],
    )
    price, _ = calculate_raid_payment(participant, raid_prices)
    assert price == expected_price


def test_download_security_files_zip(client: TestClient):
    response = client.get(
        "/raid/security_files_zip",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 200


def test_download_team_files_zip(client: TestClient):
    response = client.get(
        "/raid/team_files_zip",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 200


def test_delete_all_teams(client: TestClient):
    response = client.delete(
        "/raid/teams",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/raid/teams",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_download_security_files_zip_with_no_teams(client: TestClient):
    response = client.get(
        "/raid/security_files_zip",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 400


def test_download_team_files_zip_with_no_teams(client: TestClient):
    response = client.get(
        "/raid/team_files_zip",
        headers={"Authorization": f"Bearer {token_raid_admin}"},
    )
    assert response.status_code == 400


# Tests for JSON file endpoints


def test_get_json_file_success(client: TestClient, mocker: MockerFixture):
    """Test successful retrieval of a JSON file."""
    test_content = {"key": "value", "nested": {"data": "test"}}

    # Mock the file operations
    mock_file_path = mocker.Mock()
    mock_file_path.exists.return_value = True

    # Create a proper mock for the context manager
    mock_file = mocker.mock_open(read_data=json.dumps(test_content))
    mock_file_path.open = mock_file

    mocker.patch(
        "app.modules.raid.endpoints_raid.get_file_from_data",
        return_value=mock_file_path,
    )
    mocker.patch("json.load", return_value=test_content)

    response = client.get(
        "/raid/chrono_raid/json/test_file",
        headers={"Authorization": f"Bearer {token_raid_volunteer}"},
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["name"] == "test_file"
    assert response_data["content"] == test_content


def test_get_json_file_not_found(client: TestClient, mocker: MockerFixture):
    """Test retrieval of a JSON file that doesn't exist."""
    # Mock the file operations
    mock_file_path = mocker.Mock()
    mock_file_path.exists.return_value = False

    mocker.patch(
        "app.modules.raid.endpoints_raid.get_file_from_data",
        return_value=mock_file_path,
    )

    response = client.get(
        "/raid/chrono_raid/json/nonexistent_file",
        headers={"Authorization": f"Bearer {token_raid_volunteer}"},
    )

    assert response.status_code == 404
    assert "introuvable" in response.json()["detail"]


def test_get_json_file_unauthorized(client: TestClient):
    """Test retrieval of a JSON file without proper authorization."""
    response = client.get(
        "/raid/chrono_raid/json/test_file",
        headers={"Authorization": f"Bearer {token_simple}"},
    )

    assert response.status_code == 403


def test_save_json_file_success(client: TestClient, mocker: MockerFixture):
    """Test successful saving of a JSON file."""
    test_content = {"key": "value", "array": [1, 2, 3]}
    request_data = {
        "name": "test_save_file",
        "content": test_content,
    }

    # Mock the file operations with proper context manager
    mock_file_path = mocker.Mock()
    mock_file = mocker.mock_open()
    mock_file_path.open = mock_file

    mocker.patch(
        "app.modules.raid.endpoints_raid.get_file_path_from_data",
        return_value=mock_file_path,
    )
    mock_json_dump = mocker.patch("app.modules.raid.endpoints_raid.json.dump")

    response = client.post(
        "/raid/chrono_raid/json",
        json=request_data,
        headers={"Authorization": f"Bearer {token_raid_volunteer}"},
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["name"] == "test_save_file"
    assert response_data["content"] == test_content

    # Verify that json.dump was called
    mock_json_dump.assert_called_once()


def test_save_json_file_unauthorized(client: TestClient):
    """Test saving a JSON file without proper authorization."""
    request_data = {
        "name": "test_file",
        "content": {"key": "value"},
    }

    response = client.post(
        "/raid/chrono_raid/json",
        json=request_data,
        headers={"Authorization": f"Bearer {token_simple}"},
    )

    assert response.status_code == 403
