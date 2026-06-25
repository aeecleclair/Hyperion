from datetime import UTC, datetime
from unittest.mock import ANY
from uuid import UUID, uuid4

import pytest_asyncio
from documenso_sdk import DocumentDownloadResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents.models_documents import (
    DocumentDocument,
    DocumentTeam,
    DocumentTemplate,
)
from app.core.documents.types_documenso import DocumentStatus
from app.core.groups.groups_type import GroupType
from app.core.groups.models_groups import CoreGroup
from app.core.users.models_users import CoreUser
from app.types.module import Module
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

TEST_MODULE_ROOT = "Test"

group1: CoreGroup
group2: CoreGroup
group3: CoreGroup
group4: CoreGroup

user_lambda: CoreUser
user_team1: CoreUser
user_team2: CoreUser
user_admin: CoreUser

user_lambda_token: str
user_team1_token: str
user_team2_token: str
user_admin_token: str

team1: DocumentTeam
team2: DocumentTeam

templateTeam1: DocumentTemplate
templateTeam2: DocumentTemplate
templateDeleted: DocumentTemplate

documentTemplate1: DocumentDocument
documentTemplate2: DocumentDocument
documentDeleted: DocumentDocument
documentRejected: DocumentDocument
documentCompleted: DocumentDocument
documentPending: DocumentDocument
documentPending2: DocumentDocument


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global group1, group2, group3, group4
    group1 = await create_groups_with_permissions([], "Group 1")
    group2 = await create_groups_with_permissions([], "Group 2")
    group3 = await create_groups_with_permissions([], "Group 3")
    group4 = await create_groups_with_permissions([], "Group 4")

    global user_lambda, user_team1, user_team2, user_admin
    user_lambda = await create_user_with_groups([])
    user_team1 = await create_user_with_groups([group1.id])
    user_team2 = await create_user_with_groups([group2.id])
    user_admin = await create_user_with_groups([GroupType.admin])

    global user_lambda_token, user_team1_token, user_team2_token, user_admin_token
    user_lambda_token = create_api_access_token(user_lambda)
    user_team1_token = create_api_access_token(user_team1)
    user_team2_token = create_api_access_token(user_team2)
    user_admin_token = create_api_access_token(user_admin)

    global team1, team2

    team1 = DocumentTeam(
        id=uuid4(),
        team_id=1,
        group_id=group1.id,
        name="Team 1",
        api_key="api_key_1",
    )
    await add_object_to_db(team1)

    team2 = DocumentTeam(
        id=uuid4(),
        team_id=2,
        group_id=group2.id,
        name="Team 2",
        api_key="api_key_2",
    )
    await add_object_to_db(team2)

    global templateTeam1, templateTeam2, templateDeleted

    templateTeam1 = DocumentTemplate(
        id=uuid4(),
        documenso_id=1,
        name="Template 1",
        team_id=team1.id,
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 2, tzinfo=UTC),
        deleted=False,
        document_directory_id="directory_id_1",
    )
    await add_object_to_db(templateTeam1)

    templateTeam2 = DocumentTemplate(
        id=uuid4(),
        documenso_id=2,
        name="Template 2",
        team_id=team2.id,
        created_at=datetime(2023, 1, 3, tzinfo=UTC),
        updated_at=datetime(2023, 1, 4, tzinfo=UTC),
        deleted=False,
    )
    await add_object_to_db(templateTeam2)

    templateDeleted = DocumentTemplate(
        id=uuid4(),
        documenso_id=3,
        name="Template Deleted",
        team_id=team1.id,
        created_at=datetime(2023, 1, 5, tzinfo=UTC),
        updated_at=datetime(2023, 1, 6, tzinfo=UTC),
        deleted=True,
    )
    await add_object_to_db(templateDeleted)

    global \
        documentTemplate1, \
        documentTemplate2, \
        documentDeleted, \
        documentRejected, \
        documentCompleted, \
        documentPending, \
        documentPending2

    documentTemplate1 = DocumentDocument(
        id=uuid4(),
        documenso_id=1,
        name="Document 1",
        template_id=templateTeam1.id,
        module=TEST_MODULE_ROOT,
        user_id=user_lambda.id,
        signing_token="signing_token_1",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 7, tzinfo=UTC),
        updated_at=datetime(2023, 1, 8, tzinfo=UTC),
    )
    await add_object_to_db(documentTemplate1)

    documentTemplate2 = DocumentDocument(
        id=uuid4(),
        documenso_id=2,
        name="Document 2",
        template_id=templateTeam2.id,
        module="module2",
        user_id=user_lambda.id,
        signing_token="signing_token_2",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 9, tzinfo=UTC),
        updated_at=datetime(2023, 1, 10, tzinfo=UTC),
    )
    await add_object_to_db(documentTemplate2)

    documentDeleted = DocumentDocument(
        id=uuid4(),
        documenso_id=3,
        name="Document Deleted",
        template_id=templateTeam1.id,
        module=TEST_MODULE_ROOT,
        user_id=user_lambda.id,
        signing_token="signing_token_deleted",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 11, tzinfo=UTC),
        updated_at=datetime(2023, 1, 12, tzinfo=UTC),
    )
    await add_object_to_db(documentDeleted)

    documentRejected = DocumentDocument(
        id=uuid4(),
        documenso_id=4,
        name="Document Rejected",
        template_id=templateTeam1.id,
        module=TEST_MODULE_ROOT,
        user_id=user_lambda.id,
        signing_token="signing_token_rejected",
        status=DocumentStatus.REJECTED,
        created_at=datetime(2023, 1, 13, tzinfo=UTC),
        updated_at=datetime(2023, 1, 14, tzinfo=UTC),
    )
    await add_object_to_db(documentRejected)

    documentCompleted = DocumentDocument(
        id=uuid4(),
        documenso_id=5,
        name="Document Completed",
        template_id=templateTeam1.id,
        module=TEST_MODULE_ROOT,
        user_id=user_lambda.id,
        signing_token="signing_token_completed",
        status=DocumentStatus.COMPLETED,
        created_at=datetime(2023, 1, 15, tzinfo=UTC),
        updated_at=datetime(2023, 1, 16, tzinfo=UTC),
    )
    await add_object_to_db(documentCompleted)

    documentPending = DocumentDocument(
        id=uuid4(),
        documenso_id=6,
        name="Document Pending",
        template_id=templateTeam1.id,
        module=TEST_MODULE_ROOT,
        user_id=user_lambda.id,
        signing_token="signing_token_pending",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 17, tzinfo=UTC),
        updated_at=datetime(2023, 1, 18, tzinfo=UTC),
    )
    await add_object_to_db(documentPending)

    documentPending2 = DocumentDocument(
        id=uuid4(),
        documenso_id=7,
        name="Document Pending 2",
        template_id=templateTeam1.id,
        module=TEST_MODULE_ROOT,
        user_id=user_lambda.id,
        signing_token="signing_token_pending_2",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 19, tzinfo=UTC),
        updated_at=datetime(2023, 1, 20, tzinfo=UTC),
    )
    await add_object_to_db(documentPending2)


# region: Team


async def test_get_teams(client: TestClient):
    response = client.get(
        "/documents/teams/",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_teams_as_lambda(client: TestClient):
    response = client.get(
        "/documents/teams",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 403


async def test_get_user_teams(client: TestClient):
    response = client.get(
        "/documents/teams/me",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_create_team_existing_group(client: TestClient):
    response = client.post(
        "/documents/teams/",
        json={
            "team_id": 4,
            "group_id": group1.id,
            "name": "Team 4",
            "api_key": "api_key_4",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 400

    response = client.get(
        "/documents/teams/",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_create_team_existing_name(client: TestClient):
    response = client.post(
        "/documents/teams/",
        json={
            "team_id": 5,
            "group_id": group3.id,
            "name": "Team 1",
            "api_key": "api_key_5",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 400

    response = client.get(
        "/documents/teams/",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_create_team_invalid_api_key(client: TestClient):
    response = client.post(
        "/documents/teams/",
        json={
            "team_id": 6,
            "group_id": group3.id,
            "name": "Team 6",
            "api_key": "wrong_api_key",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 400
    assert str(response.json()["detail"]).startswith(
        "Failed to connect to Documenso with the provided API key:",
    )

    response = client.get(
        "/documents/teams/",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_create_team(
    client: TestClient,
    mocker: MockerFixture,
):
    mocker.patch(
        "app.core.documents.documenso_tool.DocumensoTool.find_folders",
        return_value=None,
    )
    response = client.post(
        "/documents/teams/",
        json={
            "team_id": 3,
            "group_id": group3.id,
            "name": "Team 3",
            "api_key": "api_key_3",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 201

    teams = client.get(
        "/documents/teams/",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert teams.status_code == 200
    assert len(teams.json()) == 3
    new_team = next((t for t in teams.json() if t["id"] == response.json()["id"]), None)
    assert new_team is not None


async def test_update_team_not_found(client: TestClient):
    response = client.patch(
        f"/documents/teams/{uuid4()}",
        json={
            "name": "Team Not Found",
            "group_id": group4.id,
            "api_key": "api_key_not_found",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 404


async def test_update_team_existing_name(client: TestClient):
    response = client.patch(
        f"/documents/teams/{team1.id}",
        json={
            "name": "Team 2",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 400

    response = client.get(
        "/documents/teams",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    teams = response.json()
    team1_data = next((t for t in teams if t["id"] == str(team1.id)), None)
    assert team1_data is not None
    assert team1_data["name"] == "Team 1"


async def test_update_team_existing_group(client: TestClient):
    response = client.patch(
        f"/documents/teams/{team1.id}",
        json={
            "group_id": group2.id,
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 400

    response = client.get(
        "/documents/teams",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    teams = response.json()
    team1_data = next((t for t in teams if t["id"] == str(team1.id)), None)
    assert team1_data is not None
    assert team1_data["group_id"] == str(group1.id)


async def test_update_team_invalid_api_key(client: TestClient):
    response = client.patch(
        f"/documents/teams/{team1.id}",
        json={
            "api_key": "wrong_api_key",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 400
    assert str(response.json()["detail"]).startswith(
        "Failed to connect to Documenso with the provided API key:",
    )

    response = client.get(
        "/documents/teams",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    teams = response.json()
    team1_data = next((t for t in teams if t["id"] == str(team1.id)), None)
    assert team1_data is not None
    assert team1_data["api_key"] == "api_key_1"


async def test_update_team(
    client: TestClient,
    mocker: MockerFixture,
):
    mocker.patch(
        "app.core.documents.documenso_tool.DocumensoTool.find_folders",
        return_value=None,
    )
    response = client.patch(
        f"/documents/teams/{team1.id}",
        json={
            "name": "Team 1 Updated",
            "group_id": group4.id,
            "api_key": "api_key_1_updated",
        },
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 204, response.text

    response = client.get(
        "/documents/teams",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    teams = response.json()
    team1_data = next((t for t in teams if t["id"] == str(team1.id)), None)
    assert team1_data is not None
    assert team1_data["name"] == "Team 1 Updated"
    assert team1_data["group_id"] == str(group4.id)
    assert team1_data["api_key"] == "api_key_1_updated"

    client.patch(
        f"/documents/teams/{team1.id}",
        json={"name": "Team 1", "group_id": group1.id},
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )


async def test_delete_team_not_found(client: TestClient):
    response = client.delete(
        f"/documents/teams/{uuid4()}",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 404


async def test_delete_team(client: TestClient):
    new_team = DocumentTeam(
        id=uuid4(),
        team_id=6,
        group_id=group4.id,
        name="Team 6",
        api_key="api_key_6",
    )
    await add_object_to_db(new_team)

    response = client.delete(
        f"/documents/teams/{new_team.id}",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/documents/teams",
        headers={"Authorization": f"Bearer {user_admin_token}"},
    )
    assert response.status_code == 200
    teams = response.json()
    deleted_team = next((t for t in teams if t["id"] == str(new_team.id)), None)
    assert deleted_team is None


# endregion: Team
# region: Template


async def test_get_team_templates(client: TestClient):
    response = client.get(
        f"/documents/teams/{team2.id}/templates",
        headers={"Authorization": f"Bearer {user_team2_token}"},
    )
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 1
    assert templates[0]["id"] == str(templateTeam2.id)


async def test_get_team_templates_not_found(client: TestClient):
    response = client.get(
        f"/documents/teams/{uuid4()}/templates",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 404


async def test_get_team_templates_as_lambda(client: TestClient):
    response = client.get(
        f"/documents/teams/{team1.id}/templates",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to view templates for this team"
    )


async def test_get_template_as_lambda(client: TestClient):
    response = client.get(
        f"/documents/templates/{templateTeam1.id}",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "You do not have permission to view this template"
    )


async def test_get_template_as_team_member(client: TestClient):
    response = client.get(
        f"/documents/templates/{templateTeam1.id}",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 6


async def test_get_template_not_found(client: TestClient):
    response = client.get(
        f"/documents/templates/{uuid4()}",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 404


async def test_update_template_directory(client: TestClient):
    new_directory_id = "new_directory_id"
    response = client.patch(
        f"/documents/templates/{templateTeam1.id}",
        json={"document_directory_id": new_directory_id},
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/documents/templates/{templateTeam1.id}",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200
    assert response.json()["document_directory_id"] == new_directory_id


async def test_update_template_directory_not_found(client: TestClient):
    response = client.patch(
        f"/documents/templates/{uuid4()}",
        json={"document_directory_id": "new_directory_id"},
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 404


async def test_update_template_directory_as_lambda(client: TestClient):
    response = client.patch(
        f"/documents/templates/{templateTeam1.id}",
        json={"document_directory_id": "new_directory_id"},
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to update this template"
    )


# endregion: Template
# region: Document


def test_get_user_documents(client: TestClient):
    response = client.get(
        "/documents/me",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 7


def test_get_document_token(client: TestClient):
    response = client.get(
        f"/documents/{documentTemplate1.id}/token",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert token_data["signing_token"] == documentTemplate1.signing_token


def test_get_document_token_not_found(client: TestClient):
    response = client.get(
        f"/documents/{uuid4()}/token",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 404


def test_get_document_token_as_other_user(client: TestClient):
    response = client.get(
        f"/documents/{documentTemplate1.id}/token",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Access forbidden"


def test_download_document_unknown_document(client: TestClient):
    response = client.get(
        f"/documents/{uuid4()}/download",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_download_document_not_completed(client: TestClient):
    response = client.get(
        f"/documents/{documentPending.id}/download",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Document is not completed and cannot be downloaded"
    )


def test_download_document_as_other_user(client: TestClient):
    response = client.get(
        f"/documents/{documentCompleted.id}/download",
        headers={"Authorization": f"Bearer {user_team2_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Access forbidden"


def test_download_document_as_user(client: TestClient, mocker: MockerFixture):
    mocker.patch(
        "app.core.documents.documenso_tool.DocumensoTool.download_document",
        return_value=DocumentDownloadResponse(
            headers={},
            result=b"PDF content",
        ),
    )

    response = client.get(
        f"/documents/{documentCompleted.id}/download",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 200
    assert response.content == b'"PDF content"'


def test_download_document_as_group_admin(client: TestClient, mocker: MockerFixture):
    mocker.patch(
        "app.core.documents.documenso_tool.DocumensoTool.download_document",
        return_value=DocumentDownloadResponse(
            headers={},
            result=b"PDF content",
        ),
    )

    response = client.get(
        f"/documents/{documentCompleted.id}/download",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200
    assert response.content == b'"PDF content"'


def test_get_template_documents(client: TestClient):
    response = client.get(
        f"/documents/templates/{templateTeam1.id}/documents",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 6


def test_get_template_documents_not_found(client: TestClient):
    response = client.get(
        f"/documents/templates/{uuid4()}/documents",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 404


def test_get_template_documents_as_lambda(client: TestClient):
    response = client.get(
        f"/documents/templates/{templateTeam1.id}/documents",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to view documents for this template"
    )


class MockedRecipientResponse(BaseModel):
    token: str


class MockedTemplateUseResponse(BaseModel):
    id: int
    recipients: list[MockedRecipientResponse]
    title: str


async def test_use_template_not_found(
    client: TestClient,
):
    response = client.post(
        f"/documents/templates/{uuid4()}/documents/",
        json={"recipients": [user_lambda.email]},
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 404


async def test_use_template_as_lambda(
    client: TestClient,
):
    response = client.post(
        f"/documents/templates/{templateTeam1.id}/documents/",
        json={"recipients": [user_lambda.email]},
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "You do not have permission to use this template"
    )


async def test_use_template_invalid_destination_folder(
    client: TestClient,
):
    response = client.post(
        f"/documents/templates/{templateTeam2.id}/documents/",
        json={
            "recipients": [user_lambda.email],
        },
        headers={"Authorization": f"Bearer {user_team2_token}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "No destination folder configured for this template"
    )


async def test_use_template_for_a_recipient_user_not_found(
    client: TestClient,
):
    response = client.post(
        f"/documents/templates/{templateTeam1.id}/documents/",
        json={"recipients": ["test@test.fr"]},
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["errors"]) == 1
    assert response.json()["errors"]["test@test.fr"] == "User not found"


async def test_use_template_for_a_recipient(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_id = uuid4()
    mocker.patch(
        "app.core.documents.utils_documents.uuid.uuid4",
        return_value=mocked_id,
    )
    mocker.patch(
        "app.core.documents.documenso_tool.DocumensoTool.use_template",
        return_value=MockedTemplateUseResponse(
            id=100,
            recipients=[MockedRecipientResponse(token="mocked_signing_token")],
            title="Mocked Document Title",
        ),
    )
    response = client.post(
        f"/documents/templates/{templateTeam1.id}/documents/",
        json={"recipients": [user_lambda.email]},
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 201, response.text
    response_data = response.json()
    assert len(response_data["errors"]) == 0
    assert len(response_data["documents"]) == 1

    documents = client.get(
        f"/documents/templates/{templateTeam1.id}/documents",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert documents.status_code == 200
    assert any(doc["id"] == str(mocked_id) for doc in documents.json())


# endregion: Document
# region: Webhook
async def test_webhook_template_creation_invalid_secret(
    client: TestClient,
):
    json = {
        "event": "TEMPLATE_CREATED",
        "payload": {
            "id": 10,
            "externalId": None,
            "title": "My Template",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:00.631Z",
            "updatedAt": "2026-06-16T13:44:00.631Z",
        },
        "createdAt": "2026-06-16T13:44:00.631Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "invalidsecret",
        },
    )
    assert response.status_code == 403


async def test_webhook_template_creation_invalid_payload(
    client: TestClient,
):
    json = {
        "event": "TEMPLATE_CREATED",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 422


async def test_webhook_template_creation_unknown_team(
    client: TestClient,
    mocker: MockerFixture,
):

    mocked_creation = mocker.patch(
        "app.core.documents.utils_documents.cruds_documents.create_template",
        return_value=None,
    )
    json = {
        "event": "TEMPLATE_CREATED",
        "payload": {
            "id": 11,
            "externalId": None,
            "title": "My Template Unknown Team",
            "status": "DRAFT",
            "teamId": 9999,
            "source": "TEMPLATE",
            "recipients": [{"id": 53, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:00.631Z",
            "updatedAt": "2026-06-16T13:44:00.631Z",
        },
        "createdAt": "2026-06-16T13:44:00.631Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_creation.assert_not_called()


async def test_webhook_template_creation_multiple_recipients(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_creation = mocker.patch(
        "app.core.documents.utils_documents.cruds_documents.create_template",
        return_value=None,
    )
    json = {
        "event": "TEMPLATE_CREATED",
        "payload": {
            "id": 12,
            "externalId": None,
            "title": "My Template Multiple Recipients",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [
                {"id": 54, "token": "SIGNING_TOKEN_1"},
                {"id": 55, "token": "SIGNING_TOKEN_2"},
            ],
            "createdAt": "2026-06-16T13:44:00.631Z",
            "updatedAt": "2026-06-16T13:44:00.631Z",
        },
        "createdAt": "2026-06-16T13:44:00.631Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_creation.assert_not_called()


async def test_webhook_template_creation_missing_team(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_creation = mocker.patch(
        "app.core.documents.utils_documents.cruds_documents.create_template",
        return_value=None,
    )
    json = {
        "event": "TEMPLATE_CREATED",
        "payload": {
            "id": 13,
            "externalId": None,
            "title": "My Template Missing Team",
            "status": "DRAFT",
            "teamId": None,
            "source": "TEMPLATE",
            "recipients": [{"id": 56, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:00.631Z",
            "updatedAt": "2026-06-16T13:44:00.631Z",
        },
        "createdAt": "2026-06-16T13:44:00.631Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_creation.assert_not_called()


async def test_webhook_template_creation(
    client: TestClient,
):
    json = {
        "event": "TEMPLATE_CREATED",
        "payload": {
            "id": 10,
            "externalId": None,
            "title": "My Template",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:00.631Z",
            "updatedAt": "2026-06-16T13:44:00.631Z",
        },
        "createdAt": "2026-06-16T13:44:00.631Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    templates = client.get(
        f"/documents/teams/{team1.id}/templates",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert templates.status_code == 200
    template = next((t for t in templates.json() if t["documenso_id"] == 10), None)
    assert template is not None
    assert template["name"] == "My Template"


async def test_webhook_template_update_unknown_template(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_template",
        return_value=None,
    )
    json = {
        "event": "TEMPLATE_UPDATED",
        "payload": {
            "id": 9999,
            "externalId": None,
            "title": "My Updated Template",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:05.967Z",
            "updatedAt": "2026-06-16T13:44:05.967Z",
        },
        "createdAt": "2026-06-16T13:44:05.967Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_template_update(
    client: TestClient,
):
    template = DocumentTemplate(
        id=uuid4(),
        documenso_id=11,
        name="My Template",
        team_id=team1.id,
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 2, tzinfo=UTC),
        deleted=False,
    )
    await add_object_to_db(template)

    json = {
        "event": "TEMPLATE_UPDATED",
        "payload": {
            "id": 11,
            "externalId": None,
            "title": "My Updated Template",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:05.967Z",
            "updatedAt": "2026-06-16T13:44:05.967Z",
        },
        "createdAt": "2026-06-16T13:44:05.967Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    templates = client.get(
        f"/documents/teams/{team1.id}/templates",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert templates.status_code == 200
    db_template = next(
        (t for t in templates.json() if t["id"] == str(template.id)),
        None,
    )
    assert db_template is not None
    assert db_template["name"] == "My Updated Template"


async def test_webhook_template_deletion_unknown_template(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_deletion = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_template",
        return_value=None,
    )
    json = {
        "event": "TEMPLATE_DELETED",
        "payload": {
            "id": 9999,
            "externalId": None,
            "title": "Deleted Template",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:09.725Z",
            "updatedAt": "2026-06-16T13:44:09.725Z",
        },
        "createdAt": "2026-06-16T13:44:09.725Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_deletion.assert_not_called()


async def test_webhook_template_deletion(
    client: TestClient,
):
    template = DocumentTemplate(
        id=uuid4(),
        documenso_id=12,
        name="My Template",
        team_id=team1.id,
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 2, tzinfo=UTC),
        deleted=False,
    )
    await add_object_to_db(template)

    json = {
        "event": "TEMPLATE_DELETED",
        "payload": {
            "id": 12,
            "externalId": None,
            "title": "Deleted Template",
            "status": "DRAFT",
            "teamId": 1,
            "source": "TEMPLATE",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:09.725Z",
            "updatedAt": "2026-06-16T13:44:09.725Z",
        },
        "createdAt": "2026-06-16T13:44:09.725Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    templates = client.get(
        f"/documents/teams/{team1.id}/templates",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert templates.status_code == 200
    db_template = next(
        (t for t in templates.json() if t["id"] == str(template.id)),
        None,
    )
    assert db_template is not None
    assert db_template["deleted"] is True


async def callback(
    document_id: UUID,
    status: DocumentStatus,
    db: AsyncSession,
) -> None:
    pass


async def test_webhook_document_completed_empty_external_id(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_document",
        return_value=None,
    )
    json = {
        "event": "DOCUMENT_COMPLETED",
        "payload": {
            "id": 9999,
            "externalId": None,
            "title": "documenso.pdf",
            "status": "COMPLETED",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 50, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:25.475Z",
            "updatedAt": "2026-06-16T13:44:25.475Z",
            "completedAt": "2026-06-16T13:44:25.475Z",
        },
        "createdAt": "2026-06-16T13:44:25.475Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_document_completed_unknown_document(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_document",
        return_value=None,
    )
    json = {
        "event": "DOCUMENT_COMPLETED",
        "payload": {
            "id": 9999,
            "externalId": str(uuid4()),
            "title": "documenso.pdf",
            "status": "COMPLETED",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 50, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:25.475Z",
            "updatedAt": "2026-06-16T13:44:25.475Z",
            "completedAt": "2026-06-16T13:44:25.475Z",
        },
        "createdAt": "2026-06-16T13:44:25.475Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_document_completed_already_completed(
    client: TestClient,
    mocker: MockerFixture,
):

    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_document",
        return_value=None,
    )
    json = {
        "event": "DOCUMENT_COMPLETED",
        "payload": {
            "id": 20,
            "externalId": str(documentCompleted.id),
            "title": "documenso.pdf",
            "status": "COMPLETED",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 50, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:25.475Z",
            "updatedAt": "2026-06-16T13:44:25.475Z",
            "completedAt": "2026-06-16T13:44:25.475Z",
        },
        "createdAt": "2026-06-16T13:44:25.475Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_document_completed(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_callback = mocker.patch(
        "tests.core.test_documents.callback",
    )
    test_module = Module(
        root=TEST_MODULE_ROOT,
        tag="Tests",
        default_allowed_groups_ids=[],
        document_callback=callback,
        factory=None,
        permissions=None,
    )
    mocker.patch(
        "app.core.documents.utils_documents.all_modules",
        [test_module],
    )

    json = {
        "event": "DOCUMENT_COMPLETED",
        "payload": {
            "id": 21,
            "externalId": str(documentPending.id),
            "title": "documenso.pdf",
            "status": "COMPLETED",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 50, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:25.475Z",
            "updatedAt": "2026-06-16T13:44:25.475Z",
            "completedAt": "2026-06-16T13:44:25.475Z",
        },
        "createdAt": "2026-06-16T13:44:25.475Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200
    mocked_callback.assert_called_once_with(
        documentPending.id,
        DocumentStatus.COMPLETED,
        ANY,
    )


async def test_webhook_document_rejected_empty_external_id(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_document",
        return_value=None,
    )
    json = {
        "event": "DOCUMENT_REJECTED",
        "payload": {
            "id": 10,
            "externalId": None,
            "title": "documenso.pdf",
            "status": "PENDING",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:33.055Z",
            "updatedAt": "2026-06-16T13:44:33.055Z",
        },
        "createdAt": "2026-06-16T13:44:33.055Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_document_rejected_unknown_document(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_document",
        return_value=None,
    )
    json = {
        "event": "DOCUMENT_REJECTED",
        "payload": {
            "id": 10,
            "externalId": str(uuid4()),
            "title": "documenso.pdf",
            "status": "PENDING",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:33.055Z",
            "updatedAt": "2026-06-16T13:44:33.055Z",
        },
        "createdAt": "2026-06-16T13:44:33.055Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_document_rejected_already_rejected(
    client: TestClient,
    mocker: MockerFixture,
):
    mocked_update = mocker.patch(
        "app.core.documents.endpoints_documents.cruds_documents.update_document",
        return_value=None,
    )
    json = {
        "event": "DOCUMENT_REJECTED",
        "payload": {
            "id": 10,
            "externalId": str(documentRejected.id),
            "title": "documenso.pdf",
            "status": "PENDING",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:33.055Z",
            "updatedAt": "2026-06-16T13:44:33.055Z",
        },
        "createdAt": "2026-06-16T13:44:33.055Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200

    mocked_update.assert_not_called()


async def test_webhook_document_rejected(
    client: TestClient,
    mocker: MockerFixture,
):

    mocked_callback = mocker.patch(
        "tests.core.test_documents.callback",
    )
    test_module = Module(
        root=TEST_MODULE_ROOT,
        tag="Tests",
        default_allowed_groups_ids=[],
        document_callback=callback,
        factory=None,
        permissions=None,
    )
    mocker.patch(
        "app.core.documents.utils_documents.all_modules",
        [test_module],
    )

    json = {
        "event": "DOCUMENT_REJECTED",
        "payload": {
            "id": 10,
            "externalId": str(documentPending2.id),
            "title": "documenso.pdf",
            "status": "PENDING",
            "teamId": 1,
            "source": "DOCUMENT",
            "recipients": [{"id": 52, "token": "SIGNING_TOKEN"}],
            "createdAt": "2026-06-16T13:44:33.055Z",
            "updatedAt": "2026-06-16T13:44:33.055Z",
        },
        "createdAt": "2026-06-16T13:44:33.055Z",
        "webhookEndpoint": "https://webhook.site/a2056231-ff10-4818-9d70-9b112739f9bd",
    }
    response = client.post(
        "/documents/webhook/",
        json=json,
        headers={
            "Authorization": f"Bearer {user_admin_token}",
            "X-Documenso-Secret": "somestrongsecret",
        },
    )
    assert response.status_code == 200
    mocked_callback.assert_called_once_with(
        documentPending2.id,
        DocumentStatus.REJECTED,
        ANY,
    )
