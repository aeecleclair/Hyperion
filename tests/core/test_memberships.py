import uuid
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_mock import MockerFixture

from app.core.documents import models_documents
from app.core.documents.types_documenso import DocumentStatus
from app.core.groups import models_groups
from app.core.groups.groups_type import GroupType
from app.core.memberships import cruds_memberships, models_memberships
from app.core.memberships.utils_memberships import (
    MODULE_ROOT,
    membership_document_callback,
)
from app.core.users import models_users
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
    get_TestingSessionLocal,
)

bde_group: models_groups.CoreGroup
bds_group: models_groups.CoreGroup
dummy_group_1: models_groups.CoreGroup
dummy_group_2: models_groups.CoreGroup

user: models_users.CoreUser
admin_user: models_users.CoreUser
bde_user: models_users.CoreUser

token_user: str
token_admin: str
token_bde: str

team: models_documents.DocumentTeam
template: models_documents.DocumentTemplate
document: models_documents.DocumentDocument

aeecl_association_membership: models_memberships.CoreAssociationMembership
useecl_association_membership: models_memberships.CoreAssociationMembership
aeecl_user_membership: models_memberships.CoreAssociationUserMembership
useecl_user_membership: models_memberships.CoreAssociationUserMembership


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global bde_group, bds_group, dummy_group_1, dummy_group_2
    bde_group = await create_groups_with_permissions(
        [],
        "BDE Group",
    )
    bds_group = await create_groups_with_permissions(
        [],
        "BDS Group",
    )
    dummy_group_1 = await create_groups_with_permissions(
        [],
        "Dummy Group 1",
    )
    dummy_group_2 = await create_groups_with_permissions(
        [],
        "Dummy Group 2",
    )

    global user, admin_user, bde_user
    user = await create_user_with_groups([])
    admin_user = await create_user_with_groups(
        [GroupType.admin],
    )
    bde_user = await create_user_with_groups(
        [bde_group.id],
    )

    global token_user, token_admin, token_bde
    token_user = create_api_access_token(user)
    token_admin = create_api_access_token(admin_user)
    token_bde = create_api_access_token(bde_user)

    global team, template, document
    team = models_documents.DocumentTeam(
        id=uuid.uuid4(),
        team_id=1,
        group_id=bds_group.id,
        name="Team",
        api_key="team",
    )
    await add_object_to_db(team)

    template = models_documents.DocumentTemplate(
        id=uuid.uuid4(),
        documenso_id=1,
        name="Template",
        recipient_id=1,
        team_id=team.id,
        generate_email=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        deleted=False,
        document_directory_id="1",
    )
    await add_object_to_db(template)

    document = models_documents.DocumentDocument(
        id=uuid.uuid4(),
        documenso_id=1,
        name="Document",
        template_id=template.id,
        module=MODULE_ROOT,
        user_id=user.id,
        status=DocumentStatus.COMPLETED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        signing_token="token",
    )
    await add_object_to_db(document)

    global aeecl_association_membership, useecl_association_membership
    aeecl_association_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="AEECL",
        manager_group_id=bde_group.id,
    )
    await add_object_to_db(aeecl_association_membership)
    useecl_association_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="USEECL",
        manager_group_id=bds_group.id,
        template_id=template.id,
    )
    await add_object_to_db(useecl_association_membership)

    global aeecl_user_membership, useecl_user_membership
    aeecl_user_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(aeecl_user_membership)

    useecl_user_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=100),
        end_date=datetime.now(tz=UTC).date(),
        document_id=document.id,
        document_status=DocumentStatus.PENDING,
    )
    await add_object_to_db(useecl_user_membership)


def test_get_association_memberships(client: TestClient):
    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]
    assert str(useecl_association_membership.id) in [x["id"] for x in response.json()]


def test_get_association_membership_unknown(client: TestClient):
    response = client.get(
        f"/memberships/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 404


def test_get_association_membership_lambda(client: TestClient):
    response = client.get(
        f"/memberships/{useecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_association_membership_admin(client: TestClient):
    response = client.get(
        f"/memberships/{useecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(useecl_association_membership.id)
    assert response.json()["name"] == useecl_association_membership.name
    assert (
        response.json()["manager_group_id"]
        == useecl_association_membership.manager_group_id
    )
    assert response.json()["template_id"] == str(
        useecl_association_membership.template_id,
    )
    assert response.json()["template"]["id"] == str(template.id)


def test_create_association_membership_user(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_1.id,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    membership_response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert membership_response.status_code == 200
    assert len(membership_response.json()) == 2


def test_create_association_membership_duplicate_name(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": aeecl_association_membership.name,
            "manager_group_id": dummy_group_1.id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"A membership with the name {aeecl_association_membership.name} already exists"
    )

    membership_response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert membership_response.status_code == 200
    assert len(membership_response.json()) == 2


def test_create_association_membership_unknown_manager_group(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Manager group not found"

    membership_response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert membership_response.status_code == 200
    assert len(membership_response.json()) == 2


def test_create_association_membership_unknown_template(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_1.id,
            "template_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Template not found"

    membership_response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert membership_response.status_code == 200
    assert len(membership_response.json()) == 2


def test_create_association_membership_wrong_template_team(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_1.id,
            "template_id": str(template.id),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Template team group does not match membership manager group"
    )

    membership_response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert membership_response.status_code == 200
    assert len(membership_response.json()) == 2


def test_create_association_membership_admin(client: TestClient):
    response = client.post(
        "/memberships",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_1.id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])
    membership_name = response.json()["name"]
    membership_group_id = response.json()["manager_group_id"]

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership_id) in [x["id"] for x in response.json()]
    assert membership_name in [x["name"] for x in response.json()]
    assert membership_group_id in [x["manager_group_id"] for x in response.json()]


def test_delete_association_membership_user(client: TestClient):
    response = client.delete(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]


def test_delete_association_membership_wrong_id(client: TestClient):
    response = client.delete(
        f"/memberships/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_delete_association_membership_with_users(client: TestClient):
    response = client.delete(
        f"/memberships/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(aeecl_association_membership.id) in [x["id"] for x in response.json()]


async def test_delete_association_membership_admin(client: TestClient):
    new_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Random Association1",
        manager_group_id=dummy_group_1.id,
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership.id) not in [x["id"] for x in response.json()]


def test_patch_association_membership_unknown(client: TestClient):
    response = client.patch(
        f"/memberships/{uuid.uuid4()}",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_2.id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_patch_association_membership_user(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={
            "name": "Random Association",
            "manager_group_id": dummy_group_2.id,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert aeecl_association_membership.name in [x["name"] for x in response.json()]
    assert aeecl_association_membership.manager_group_id in [
        x["manager_group_id"] for x in response.json()
    ]


async def test_patch_association_membership_unknown_manager_group(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={
            "name": "Random Association3",
            "manager_group_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Manager group not found"


async def test_patch_association_membership_duplicate_name(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={
            "name": useecl_association_membership.name,
            "manager_group_id": dummy_group_2.id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"A membership with the name {useecl_association_membership.name} already exists"
    )


async def test_patch_association_membership_unknown_template(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={
            "name": "Random Association3",
            "manager_group_id": dummy_group_2.id,
            "template_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Template not found"


async def test_patch_association_membership_wrong_template_team(client: TestClient):
    response = client.patch(
        f"/memberships/{aeecl_association_membership.id}",
        json={
            "name": "Random Association3",
            "manager_group_id": dummy_group_2.id,
            "template_id": str(template.id),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Template team group does not match membership manager group"
    )


async def test_patch_association_membership_admin(client: TestClient):
    new_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Random Association2",
        manager_group_id=dummy_group_1.id,
    )
    await add_object_to_db(new_membership)

    new_name = "Random Association3"
    new_group_id = dummy_group_2.id
    response = client.patch(
        f"/memberships/{new_membership.id}",
        json={
            "name": new_name,
            "manager_group_id": new_group_id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/memberships",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert new_name in [x["name"] for x in response.json()]
    assert new_group_id in [x["manager_group_id"] for x in response.json()]


async def test_document_renewal_unknown_membership(client: TestClient):
    response = client.post(
        f"/memberships/{uuid.uuid4()}/renew-documents",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"active_date": datetime.now(tz=UTC).date().isoformat()},
    )
    assert response.status_code == 404


async def test_document_renewal_user(client: TestClient):
    response = client.post(
        f"/memberships/{useecl_association_membership.id}/renew-documents",
        headers={"Authorization": f"Bearer {token_user}"},
        json={"active_date": datetime.now(tz=UTC).date().isoformat()},
    )
    assert response.status_code == 403


async def test_document_renewal_no_template_id(client: TestClient):
    response = client.post(
        f"/memberships/{aeecl_association_membership.id}/renew-documents",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"active_date": datetime.now(tz=UTC).date().isoformat()},
    )
    assert response.status_code == 400


class MockedRecipientResponse(BaseModel):
    token: str


class MockedTemplateUseResponse(BaseModel):
    id: int
    recipients: list[MockedRecipientResponse]
    title: str


async def test_document_renewal_admin(client: TestClient, mocker: MockerFixture):
    mocked_id = uuid4()
    mocker.patch(
        "app.core.documents.utils_documents.uuid.uuid4",
        return_value=mocked_id,
    )
    mock_use = mocker.patch(
        "app.core.documents.documenso_api_wrapper.DocumensoAPIWrapper.use_template",
        return_value=MockedTemplateUseResponse(
            id=100,
            recipients=[MockedRecipientResponse(token="mocked_signing_token")],
            title="Mocked Document Title",
        ),
    )
    targeted_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=1000),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=750),
    )
    await add_object_to_db(targeted_membership)

    response = client.post(
        f"/memberships/{useecl_association_membership.id}/renew-documents",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "active_date": (datetime.now(tz=UTC) + timedelta(days=2))
            .date()
            .isoformat(),
        },
    )
    assert response.status_code == 201
    assert mock_use.called

    membership_response = client.get(
        f"/memberships/users/{admin_user.id}/{useecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert membership_response.status_code == 200
    membership_data = membership_response.json()[0]
    assert membership_data["document_id"] == str(mocked_id)


def test_get_memberships_by_user_id_user(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(aeecl_user_membership.id) in [x["id"] for x in response.json()]


def test_get_memberships_by_user_id_admin(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(aeecl_user_membership.id) in [x["id"] for x in response.json()]


def test_get_memberships_by_user_id_manager(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(aeecl_user_membership.id) in [x["id"] for x in response.json()]
    assert str(useecl_user_membership.id) not in [x["id"] for x in response.json()]


def test_get_association_membership_by_user_id_manager(client: TestClient):
    response = client.get(
        f"/memberships/users/{user.id}/{aeecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(aeecl_user_membership.id) in [x["id"] for x in response.json()]


async def test_get_membership_members_unknown(client: TestClient):
    response = client.get(
        f"/memberships/{uuid.uuid4()}/members",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


async def test_get_membership_members_user(client: TestClient):
    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_get_membership_members_with_date_filter(client: TestClient):
    today = datetime.now(tz=UTC).date()
    new_membership1 = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=10),
    )
    new_membership2 = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=today - timedelta(days=20),
        end_date=today + timedelta(days=20),
    )

    await add_object_to_db(new_membership1)
    await add_object_to_db(new_membership2)
    membership_ids = [
        new_membership1.id,
        new_membership2.id,
    ]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    for membership_id in membership_ids:
        assert str(membership_id) in [x["id"] for x in response.json()]

    minus_fifteen_days = today - timedelta(days=15)
    plus_fifteen_days = today + timedelta(days=15)

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?minimalStartDate={minus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) in [x["id"] for x in response.json()]
    assert str(new_membership2.id) not in [x["id"] for x in response.json()]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?maximalStartDate={minus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) not in [x["id"] for x in response.json()]
    assert str(new_membership2.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?minimalEndDate={plus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) not in [x["id"] for x in response.json()]
    assert str(new_membership2.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/memberships/{useecl_association_membership.id}/members?maximalEndDate={plus_fifteen_days.strftime('%Y-%m-%d')}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership1.id) in [x["id"] for x in response.json()]
    assert str(new_membership2.id) not in [x["id"] for x in response.json()]


def test_create_user_membership_user(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(aeecl_association_membership.id),
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_user_membership_wrong_association_id(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(uuid.uuid4()),
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_create_user_membership_with_wrong_dates(client: TestClient):
    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(date(2028, 6, 1)),
            "end_date": str(date(2024, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_user_membership_with_overlapping_dates(client: TestClient):
    today = datetime.now(tz=UTC).date()

    response = client.post(
        f"/memberships/users/{user.id}",
        json={
            "association_membership_id": str(aeecl_association_membership.id),
            "start_date": str(today),
            "end_date": str(today + timedelta(days=365)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_user_membership_admin(client: TestClient, mocker: MockerFixture):
    mock_use = mocker.patch(
        "app.core.documents.documenso_api_wrapper.DocumensoAPIWrapper.use_template",
        return_value=MockedTemplateUseResponse(
            id=101,
            recipients=[MockedRecipientResponse(token="mocked_signing_token")],
            title="Mocked Document Title",
        ),
    )

    today = datetime.now(tz=UTC).date()
    response = client.post(
        f"/memberships/users/{bde_user.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(today - timedelta(days=1000)),
            "end_date": str(today - timedelta(days=750)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    assert mock_use.called
    membership_id = response.json()["id"]

    response = client.get(
        f"/memberships/users/{bde_user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert membership_id in [x["id"] for x in response.json()]


def test_create_user_membership_manager(client: TestClient):
    today = datetime.now(tz=UTC).date()
    response = client.post(
        f"/memberships/users/{bde_user.id}",
        json={
            "association_membership_id": str(aeecl_association_membership.id),
            "start_date": str(today - timedelta(days=1000)),
            "end_date": str(today - timedelta(days=750)),
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])

    memberships_response = client.get(
        f"/memberships/users/{bde_user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert memberships_response.status_code == 200
    assert str(membership_id) in [x["id"] for x in memberships_response.json()], (
        response.json()
    )


def test_delete_user_membership_user(client: TestClient):
    response = client.delete(
        f"/memberships/users/{aeecl_user_membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(aeecl_user_membership.id) in [x["id"] for x in response.json()]


def test_delete_user_membership_wrong_id(client: TestClient):
    response = client.delete(
        f"/memberships/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


async def test_delete_user_membership_admin(client: TestClient, mocker: MockerFixture):
    mock_delete = mocker.patch(
        "app.core.documents.documenso_api_wrapper.DocumensoAPIWrapper.delete_document",
        return_value=None,
    )

    new_document = models_documents.DocumentDocument(
        id=uuid.uuid4(),
        documenso_id=2,
        name="Document",
        template_id=template.id,
        module=MODULE_ROOT,
        user_id=user.id,
        status=DocumentStatus.COMPLETED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        signing_token="token",
    )
    await add_object_to_db(new_document)

    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
        document_id=new_document.id,
        document_status=DocumentStatus.COMPLETED,
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/users/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    assert mock_delete.called

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership.id) not in [x["id"] for x in response.json()]


async def test_delete_user_membership_manager(
    client: TestClient,
    mocker: MockerFixture,
):
    mock_delete = mocker.patch(
        "app.core.documents.documenso_api_wrapper.DocumensoAPIWrapper.delete_document",
        return_value=None,
    )

    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=bde_user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(new_membership)

    response = client.delete(
        f"/memberships/users/{new_membership.id}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204
    assert not mock_delete.called

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(new_membership.id) not in [x["id"] for x in response.json()]


def test_patch_user_membership_user(client: TestClient):
    response = client.patch(
        f"/memberships/users/{aeecl_user_membership.id}",
        json={
            "association_membership_id": str(useecl_association_membership.id),
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_patch_user_membership_wrong_id(client: TestClient):
    response = client.patch(
        f"/memberships/users/{uuid.uuid4()}",
        json={
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_patch_user_membership_with_wrong_dates(client: TestClient):
    response = client.patch(
        f"/memberships/users/{aeecl_user_membership.id}",
        json={
            "start_date": str(date(2028, 6, 1)),
            "end_date": str(date(2024, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


async def test_patch_user_membership_admin_overlapping_dates(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() + timedelta(days=20),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=70),
    )
    await add_object_to_db(new_membership)

    new_start_date = str(datetime.now(tz=UTC).date() - timedelta(days=50))
    new_end_date = str(datetime.now(tz=UTC).date() + timedelta(days=50))

    response = client.patch(
        f"/memberships/users/{new_membership.id}",
        json={
            "start_date": new_start_date,
            "end_date": new_end_date,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


async def test_patch_user_membership_admin(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=aeecl_user_membership.end_date + timedelta(days=90),
        end_date=aeecl_user_membership.end_date + timedelta(days=500),
    )
    await add_object_to_db(new_membership)

    new_start_date = str(aeecl_user_membership.end_date + timedelta(days=100))
    new_end_date = str(aeecl_user_membership.end_date + timedelta(days=1000))
    response = client.patch(
        f"/memberships/users/{new_membership.id}",
        json={
            "start_date": new_start_date,
            "end_date": new_end_date,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    membership = next(x for x in response.json() if x["id"] == str(new_membership.id))
    assert new_start_date == membership["start_date"]
    assert new_end_date == membership["end_date"]
    assert user.id == membership["user_id"]
    assert new_membership.id == uuid.UUID(membership["id"])


async def test_patch_user_membership_manager(client: TestClient):
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=bde_user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=aeecl_user_membership.end_date + timedelta(days=90),
        end_date=aeecl_user_membership.end_date + timedelta(days=500),
    )
    await add_object_to_db(new_membership)

    new_start_date = str(aeecl_user_membership.end_date + timedelta(days=100))
    new_end_date = str(aeecl_user_membership.end_date + timedelta(days=1000))
    response = client.patch(
        f"/memberships/users/{new_membership.id}",
        json={
            "start_date": new_start_date,
            "end_date": new_end_date,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/memberships/users/{bde_user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    membership = next(x for x in response.json() if x["id"] == str(new_membership.id))
    assert new_start_date == membership["start_date"]
    assert new_end_date == membership["end_date"]
    assert bde_user.id == membership["user_id"]
    assert new_membership.id == uuid.UUID(membership["id"])


def test_post_batch_user_memberships_user(client: TestClient):
    response = client.post(
        f"/memberships/{aeecl_association_membership.id}/add-batch/",
        json=[
            {
                "user_email": user.email,
                "start_date": str(date(2024, 6, 1)),
                "end_date": str(date(2028, 6, 1)),
            },
            {
                "user_email": user.email,
                "start_date": str(date(2024, 6, 1)),
                "end_date": str(date(2028, 6, 1)),
            },
        ],
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_post_batch_user_memberships_admin(client: TestClient):
    today = datetime.now(tz=UTC).date()
    new_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=user.id,
        association_membership_id=aeecl_association_membership.id,
        start_date=today - timedelta(days=1000),
        end_date=today + timedelta(days=365),
    )
    await add_object_to_db(new_membership)

    response = client.post(
        f"/memberships/{aeecl_association_membership.id}/add-batch/",
        json=[
            {
                "user_email": user.email,
                "start_date": str(today - timedelta(days=1000)),
                "end_date": str(today + timedelta(days=365)),
            },
            {
                "user_email": user.email,
                "start_date": str(date(2018, 6, 1)),
                "end_date": str(date(2019, 6, 1)),
            },
        ],
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/memberships/users/{user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    aeecl_memberships = [
        x
        for x in response.json()
        if x["association_membership_id"] == str(aeecl_association_membership.id)
    ]
    membership = next(
        (
            x
            for x in aeecl_memberships
            if x["start_date"] == str(today - timedelta(days=1000))
            and x["end_date"] == str(today + timedelta(days=365))
        ),
        None,
    )
    assert membership is not None
    membership = next(
        (
            x
            for x in aeecl_memberships
            if x["start_date"] == str(date(2018, 6, 1))
            and x["end_date"] == str(date(2019, 6, 1))
        ),
        None,
    )
    assert membership is not None


async def test_user_document_renewal_unknown_membership(client: TestClient):
    response = client.post(
        f"/memberships/users/{uuid.uuid4()}/renew-documents",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


async def test_user_document_renewal_user(client: TestClient):
    response = client.post(
        f"/memberships/users/{useecl_user_membership.id}/renew-documents",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_user_document_renewal_no_template_id(client: TestClient):
    response = client.post(
        f"/memberships/users/{aeecl_user_membership.id}/renew-documents",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


async def test_user_document_renewal_admin(client: TestClient, mocker: MockerFixture):
    mocked_id = uuid4()
    mocker.patch(
        "app.core.documents.utils_documents.uuid.uuid4",
        return_value=mocked_id,
    )
    mock_use = mocker.patch(
        "app.core.documents.documenso_api_wrapper.DocumensoAPIWrapper.use_template",
        return_value=MockedTemplateUseResponse(
            id=1100,
            recipients=[MockedRecipientResponse(token="mocked_signing_token")],
            title="Mocked Document Title",
        ),
    )

    targeted_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=bde_user.id,
        association_membership_id=useecl_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=1000),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=750),
    )
    await add_object_to_db(targeted_membership)

    response = client.post(
        f"/memberships/users/{targeted_membership.id}/renew-documents",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    assert mock_use.called

    membership_response = client.get(
        f"/memberships/users/{bde_user.id}/{useecl_association_membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert membership_response.status_code == 200
    assert any(
        membership["document_id"] == str(mocked_id)
        for membership in membership_response.json()
    )


async def test_synchronize(client: TestClient):
    group_membership = models_groups.CoreMembership(
        user_id=bde_user.id,
        group_id=dummy_group_1.id,
        description=None,
    )
    await add_object_to_db(group_membership)

    response = client.post(
        f"/memberships/{aeecl_association_membership.id}/group/{dummy_group_1.id}/synchronize",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/groups/{dummy_group_1.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    members = response.json()["members"]
    assert any(member["id"] == str(user.id) for member in members)
    assert not any(member["id"] == str(bde_user.id) for member in members)


async def test_document_callback(client: TestClient, mocker: MockerFixture):
    async with get_TestingSessionLocal()() as db:
        await membership_document_callback(
            db=db,
            document_id=document.id,
            document_status=DocumentStatus.COMPLETED,
        )

        membership = await cruds_memberships.get_user_membership_by_id(
            user_membership_id=useecl_user_membership.id,
            db=db,
        )
        assert membership is not None
        assert membership.document_status == DocumentStatus.COMPLETED
