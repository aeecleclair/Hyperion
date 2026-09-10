import uuid
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.users import models_users
from app.modules.identity import models_identity
from app.modules.identity.endpoints_identity import IdentityPermissions
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

group_manage_identity: models_groups.CoreGroup
group_access_identity: models_groups.CoreGroup

user: models_users.CoreUser
user_manage_identity: models_users.CoreUser
user_access_identity: models_users.CoreUser

verification_context: models_identity.VerificationContext
verification_scan_for_user: models_identity.VerificationScan

identity_token: models_identity.IdentityToken
identity_token_expired: models_identity.IdentityToken

access_token_user: str
access_token_user_manage_identity: str
access_token_user_access_identity: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global group_manage_identity, group_access_identity
    group_manage_identity = await create_groups_with_permissions(
        [IdentityPermissions.manage_identity],
        "Manage Identity",
    )
    group_access_identity = await create_groups_with_permissions(
        [IdentityPermissions.access_identity],
        "Access Identity",
    )

    global user, user_manage_identity, user_access_identity
    user = await create_user_with_groups([])
    user_manage_identity = await create_user_with_groups(
        [group_manage_identity.id, group_access_identity.id],
    )
    user_access_identity = await create_user_with_groups([group_access_identity.id])

    global \
        access_token_user, \
        access_token_user_manage_identity, \
        access_token_user_access_identity
    access_token_user = create_api_access_token(user)
    access_token_user_manage_identity = create_api_access_token(user_manage_identity)
    access_token_user_access_identity = create_api_access_token(user_access_identity)

    global verification_context
    verification_context = models_identity.VerificationContext(
        id=uuid.uuid4(),
        name="Test Verification Context",
        group_id=group_access_identity.id,
        archived=False,
    )
    await add_object_to_db(verification_context)

    global verification_scan_for_user
    verification_scan_for_user = models_identity.VerificationScan(
        id=uuid.uuid4(),
        user_id=user.id,
        verification_context_id=verification_context.id,
        datetime=datetime.now(UTC),
        scanner_user_id=user_manage_identity.id,
    )
    await add_object_to_db(verification_scan_for_user)

    global identity_token, identity_token_expired
    identity_token = models_identity.IdentityToken(
        id=uuid.uuid4(),
        token="valid_token",
        user_id=user.id,
        expire_on=datetime.now(UTC) + timedelta(hours=1),
    )
    await add_object_to_db(identity_token)
    identity_token_expired = models_identity.IdentityToken(
        id=uuid.uuid4(),
        token="expired_token",
        user_id=user.id,
        expire_on=datetime.now(UTC) - timedelta(hours=1),
    )
    await add_object_to_db(identity_token_expired)


def test_create_verification_context_for_group_not_member(client: TestClient) -> None:
    """
    Test that a user who is not a member of the group cannot create a verification context.
    """
    response = client.post(
        "/identity/verification-contexts",
        json={
            "name": "New Verification Context",
            "group_id": group_access_identity.id,
        },
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Unauthorized, user does not have the required permission"
    )


def test_create_verification_context(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can create a verification context.
    """
    response = client.post(
        "/identity/verification-contexts",
        json={
            "name": "New Verification Context",
            "group_id": group_access_identity.id,
        },
        headers={"Authorization": f"Bearer {access_token_user_manage_identity}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Verification Context"
    assert data["group_id"] == group_access_identity.id


def test_get_verification_contexts_without_contexts(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get verification contexts.
    """
    response = client.get(
        "/identity/verification-contexts",
        headers={"Authorization": f"Bearer {access_token_user}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # No contexts for this user


def test_get_verification_contexts(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get verification contexts.
    """
    response = client.get(
        "/identity/verification-contexts",
        headers={"Authorization": f"Bearer {access_token_user_manage_identity}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0  # No contexts for this user


def test_archive_verification_invalid_context_id(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can archive a verification context.
    """
    response = client.patch(
        f"/identity/verification-contexts/{uuid4()}",
        json={"archived": True},
        headers={"Authorization": f"Bearer {access_token_user_manage_identity}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Verification context not found"


def test_archive_verification_context_without_permission(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can archive a verification context.
    """
    response = client.patch(
        f"/identity/verification-contexts/{verification_context.id}",
        json={"archived": True},
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Unauthorized, user does not have the required permission"
    )


def test_archive_verification_context(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can archive a verification context.
    """
    response = client.patch(
        f"/identity/verification-contexts/{verification_context.id}",
        json={"archived": True},
        headers={"Authorization": f"Bearer {access_token_user_manage_identity}"},
    )
    assert response.status_code == 204


def test_get_identity_information_by_token_invalid_context(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get identity information by token.
    """
    response = client.get(
        f"/identity/verification-contexts/{uuid4()}/scans/{identity_token.token}/info",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Verification context not found"


def test_get_identity_information_by_token_without_permission(
    client: TestClient,
) -> None:
    """
    Test that a user who is a member of the group can get identity information by token.
    """
    response = client.get(
        f"/identity/verification-contexts/{verification_context.id}/scans/{identity_token.token}/info",
        headers={"Authorization": f"Bearer {access_token_user}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "Unauthorized to ask information for this context"
    )


def test_get_identity_information_by_token_invalid_token(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get identity information by token.
    """
    response = client.get(
        f"/identity/verification-contexts/{verification_context.id}/scans/{uuid4()}/info",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid token"


def test_get_identity_information_by_token_expired_token(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get identity information by token.
    """
    response = client.get(
        f"/identity/verification-contexts/{verification_context.id}/scans/{identity_token_expired.token}/info",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Identity token has expired"


def test_get_identity_information_by_token(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get identity information by token.
    """
    response = client.get(
        f"/identity/verification-contexts/{verification_context.id}/scans/{identity_token.token}/info",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"] == identity_token.token
    assert data["user_id"] == identity_token.user_id


def test_scan_verification_context_invalid_context(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can scan a verification context.
    """
    response = client.post(
        f"/identity/verification-contexts/{uuid4()}/scans/{identity_token.token}/scan",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Verification context not found"


def test_scan_verification_context_without_permission(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can scan a verification context.
    """
    response = client.post(
        f"/identity/verification-contexts/{verification_context.id}/scans/{identity_token.token}/scan",
        headers={"Authorization": f"Bearer {access_token_user}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "Unauthorized to ask information for this context"
    )


def test_scan_verification_context_invalid_token(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can scan a verification context.
    """
    response = client.post(
        f"/identity/verification-contexts/{verification_context.id}/scans/{uuid4()}/scan",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid token"


def test_scan_verification_context_expired_token(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can scan a verification context.
    """
    response = client.post(
        f"/identity/verification-contexts/{verification_context.id}/scans/{identity_token_expired.token}/scan",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Identity token has expired"


def test_scan_verification_context(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can scan a verification context.
    """
    response = client.post(
        f"/identity/verification-contexts/{verification_context.id}/scans/{identity_token.token}/scan",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 204


def test_get_scans_invalid_context(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get scans for a verification context.
    """
    response = client.get(
        f"/identity/verification-contexts/{uuid4()}/scans",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Verification context not found"


def test_get_scans_without_permission(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get scans for a verification context.
    """
    response = client.get(
        f"/identity/verification-contexts/{verification_context.id}/scans",
        headers={"Authorization": f"Bearer {access_token_user}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "Unauthorized to ask information for this context"
    )


def test_get_scans(client: TestClient) -> None:
    """
    Test that a user who is a member of the group can get scans for a verification context.
    """
    response = client.get(
        f"/identity/verification-contexts/{verification_context.id}/scans",
        headers={"Authorization": f"Bearer {access_token_user_access_identity}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["id"] == str(verification_scan_for_user.id)


def test_ask_for_identity_token(client: TestClient) -> None:
    """
    Test that a user can ask for an identity token.
    """
    response = client.post(
        "/identity/users/me/create-token",
        headers={"Authorization": f"Bearer {access_token_user}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expire_on" in data
