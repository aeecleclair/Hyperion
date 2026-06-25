from datetime import UTC, datetime
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_mock import MockerFixture

from app.core.documents.models_documents import (
    DocumentDocument,
    DocumentTeam,
    DocumentTemplate,
)
from app.core.documents.types_documenso import DocumentStatus
from app.core.groups.groups_type import GroupType
from app.core.groups.models_groups import CoreGroup
from app.core.users.models_users import CoreUser
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

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
        documentPending

    documentTemplate1 = DocumentDocument(
        id=uuid4(),
        name="Document 1",
        template_id=templateTeam1.id,
        module="module1",
        user_id=user_lambda.id,
        signing_token="signing_token_1",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 7, tzinfo=UTC),
        updated_at=datetime(2023, 1, 8, tzinfo=UTC),
    )
    await add_object_to_db(documentTemplate1)

    documentTemplate2 = DocumentDocument(
        id=uuid4(),
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
        name="Document Deleted",
        template_id=templateTeam1.id,
        module="module1",
        user_id=user_lambda.id,
        signing_token="signing_token_deleted",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 11, tzinfo=UTC),
        updated_at=datetime(2023, 1, 12, tzinfo=UTC),
    )
    await add_object_to_db(documentDeleted)

    documentRejected = DocumentDocument(
        id=uuid4(),
        name="Document Rejected",
        template_id=templateTeam1.id,
        module="module1",
        user_id=user_lambda.id,
        signing_token="signing_token_rejected",
        status=DocumentStatus.REJECTED,
        created_at=datetime(2023, 1, 13, tzinfo=UTC),
        updated_at=datetime(2023, 1, 14, tzinfo=UTC),
    )
    await add_object_to_db(documentRejected)

    documentCompleted = DocumentDocument(
        id=uuid4(),
        name="Document Completed",
        template_id=templateTeam1.id,
        module="module1",
        user_id=user_lambda.id,
        signing_token="signing_token_completed",
        status=DocumentStatus.COMPLETED,
        created_at=datetime(2023, 1, 15, tzinfo=UTC),
        updated_at=datetime(2023, 1, 16, tzinfo=UTC),
    )
    await add_object_to_db(documentCompleted)

    documentPending = DocumentDocument(
        id=uuid4(),
        name="Document Pending",
        template_id=templateTeam1.id,
        module="module1",
        user_id=user_lambda.id,
        signing_token="signing_token_pending",
        status=DocumentStatus.PENDING,
        created_at=datetime(2023, 1, 17, tzinfo=UTC),
        updated_at=datetime(2023, 1, 18, tzinfo=UTC),
    )
    await add_object_to_db(documentPending)


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
    assert len(response.json()["documents"]) == 5


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


def test_get_user_documents(client: TestClient):
    response = client.get(
        "/documents/me",
        headers={"Authorization": f"Bearer {user_lambda_token}"},
    )
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 6


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


def test_get_template_documents(client: TestClient):
    response = client.get(
        f"/documents/templates/{templateTeam1.id}/documents",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 5


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
    recipients: list[MockedRecipientResponse]
    title: str


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
            recipients=[MockedRecipientResponse(token="mocked_signing_token")],
            title="Mocked Document Title",
        ),
    )
    response = client.post(
        f"/documents/templates/{templateTeam1.id}/documents/",
        json={"recipient_list": [user_lambda.email]},
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert len(response_data["errors"]) == 0
    assert len(response_data["documents"]) == 1

    documents = client.get(
        f"/documents/templates/{templateTeam1.id}/documents",
        headers={"Authorization": f"Bearer {user_team1_token}"},
    )
    assert documents.status_code == 200
    assert any(doc["id"] == str(mocked_id) for doc in documents.json())
