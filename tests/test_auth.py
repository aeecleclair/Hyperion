import base64
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.auth import models_auth
from app.core.groups.groups_type import AccountType, GroupType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

user: models_core.CoreUser
external_user: models_core.CoreUser
ecl_user: models_core.CoreUser
access_token: str

valid_refresh_token = "ValidRefreshToken"
expired_refresh_token = "ExpiredRefreshToken"
revoked_refresh_token = "RevokedRefreshToken"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global user
    user = await create_user_with_groups(
        groups=[],
        email="email@myecl.fr",
        password="azerty",
    )

    global ecl_user
    ecl_user = await create_user_with_groups(
        groups=[GroupType.eclair],
        email="email@etu.ec-lyon.fr",
        password="azerty",
    )

    global external_user
    external_user = await create_user_with_groups(
        groups=[],
        account_type=AccountType.external,
        email="external@myecl.fr",
        password="azerty",
    )

    global access_token
    access_token = create_api_access_token(user)

    valid_refresh_token_db = models_auth.RefreshToken(
        client_id="",
        created_on=datetime.now(UTC),
        expire_on=datetime.now(UTC) + timedelta(days=1),
        token=valid_refresh_token,
        user_id=user.id,
        scope=None,
    )
    await add_object_to_db(valid_refresh_token_db)

    expired_refresh_token_db = models_auth.RefreshToken(
        client_id="",
        created_on=datetime.now(UTC) - timedelta(days=1),
        expire_on=datetime.now(UTC) - timedelta(days=1),
        token=expired_refresh_token,
        user_id=user.id,
        scope=None,
    )
    await add_object_to_db(expired_refresh_token_db)

    revoked_refresh_token_db = models_auth.RefreshToken(
        client_id="",
        created_on=datetime.now(UTC),
        expire_on=datetime.now(UTC) + timedelta(days=1),
        revoked_on=datetime.now(UTC),
        token=revoked_refresh_token,
        user_id=user.id,
        scope=None,
    )
    await add_object_to_db(revoked_refresh_token_db)


def test_simple_token(client: TestClient):
    response = client.post(
        "/auth/simple_token",
        data={
            "username": "email@myecl.fr",
            "password": "azerty",
        },
    )
    assert response.status_code == 200
    json = response.json()

    # Response data validation
    assert "access_token" in json
    assert json["token_type"] == "bearer"

    # The given token should not allow to access API endpoints
    response = client.get(
        "/users/",
        headers={
            "Authorization": f"Bearer {json['access_token']}",
        },
    )
    assert response.status_code == 403  # forbidden


def test_authorization_code_flow_PKCE(client: TestClient) -> None:
    code_verifier = "AntoineMonBelAntoine"
    code_challenge = "ws9GS3kBIFwDfNghvEk7GRlDvbUkSmZen8q2R4v3lBU="  # base64.urlsafe_b64encode(hashlib.sha256("AntoineMonBelAntoine".encode()).digest())
    data = {
        "client_id": "AppAuthClientWithPKCE",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data,
        follow_redirects=False,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert (url.path, query["state"][0]) == ("/docs", "azerty")
    assert query["code"][0] is not None
    code = query["code"][0]

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "client_id": "AppAuthClientWithPKCE",
        "code_verifier": code_verifier,
    }

    response = client.post("/auth/token", data=data)
    assert response.status_code == 200
    json = response.json()

    assert json["access_token"] is not None
    assert json["token_type"] == "bearer"
    assert json["expires_in"] == 1800
    assert json["refresh_token"] is not None

    refresh_token = json["refresh_token"]
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": "AppAuthClientWithPKCE",
    }
    response = client.post("/auth/token", data=data)

    assert response.status_code == 200
    json = response.json()
    assert json["refresh_token"] is not None

    used_refresh_token = refresh_token
    valid_refresh_token = json["refresh_token"]

    data = {
        "grant_type": "refresh_token",
        "refresh_token": used_refresh_token,
        "client_id": "AppAuthClientWithPKCE",
    }
    response = client.post("/auth/token", data=data)  # Try token reuse

    assert response.status_code == 400

    data = {
        "grant_type": "refresh_token",
        "refresh_token": valid_refresh_token,
        "client_id": "AppAuthClientWithPKCE",
    }
    response = client.post(
        "/auth/token",
        data=data,
    )  # Verify that the token has been revoked due to the reuse attempt

    assert response.status_code == 400


def test_authorization_code_flow_secret(client: TestClient) -> None:
    data = {
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data,
        follow_redirects=False,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert (url.path, query["state"][0]) == ("/docs", "azerty")
    assert query["code"][0] is not None
    code = query["code"][0]

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
    }

    response = client.post("/auth/token", data=data)
    assert response.status_code == 200
    json = response.json()

    assert json["access_token"] is not None
    assert json["token_type"] == "bearer"
    assert json["expires_in"] == 1800
    assert json["refresh_token"] is not None

    refresh_token = json["refresh_token"]
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
    }
    response = client.post("/auth/token", data=data)

    assert response.status_code == 200
    json = response.json()
    assert json["refresh_token"] is not None

    used_refresh_token = refresh_token
    valid_refresh_token = json["refresh_token"]

    data = {
        "grant_type": "refresh_token",
        "refresh_token": used_refresh_token,
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
    }
    response = client.post("/auth/token", data=data)  # Try token reuse

    assert response.status_code == 400

    data = {
        "grant_type": "refresh_token",
        "refresh_token": valid_refresh_token,
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
    }
    response = client.post(
        "/auth/token",
        data=data,
    )  # Verify that the token has been revoked due to the reuse attempt

    assert response.status_code == 400


def test_get_user_info(client: TestClient) -> None:
    # We first need an access token to query user info endpoints #
    data = {
        "client_id": "BaseAuthClient",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data,
        follow_redirects=False,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    code = query["code"][0]

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "client_id": "BaseAuthClient",
        "client_secret": "secret",
    }

    response = client.post("/auth/token", data=data)
    assert response.status_code == 200
    json = response.json()

    access_token = json["access_token"]

    # Query user info endpoint #
    response = client.get(
        "/auth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    json = response.json()

    assert json["name"] == user.firstname


def test_get_user_info_in_id_token(client: TestClient) -> None:
    # We first need an access token to query user info endpoints #
    data = {
        "client_id": "RalllyAuthClient",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data,
        follow_redirects=False,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    code = query["code"][0]

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "client_id": "RalllyAuthClient",
        "client_secret": "secret",
    }

    response = client.post("/auth/token", data=data)
    assert response.status_code == 200
    response_json = response.json()

    id_token = response_json["id_token"]

    # In a real application we should verify the jws signature using the provided jwk
    # Here we will just make sure the content of the token contains user info without checking the token signature

    payload = id_token.split(".")[1]
    # The string needs to be correctly padded to be able to decode it.
    # See https://stackoverflow.com/a/49459036
    decoded_payload = base64.b64decode(payload.encode("utf-8") + b"==")
    json_payload = json.loads(decoded_payload)

    assert json_payload["email"] == user.email


# Invalid service configuration
def test_authorization_code_flow_with_invalid_client_id(client: TestClient) -> None:
    data_with_invalid_client_id = {
        "client_id": "InvalidClientId",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/error?message=Invalid+client_id",
    )


# Invalid service configuration
def test_authorization_code_flow_with_invalid_redirect_uri(client: TestClient) -> None:
    data_with_invalid_client_id = {
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
        "redirect_uri": "http://invalid-redirect-uri",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/error?message=Mismatching+redirect_uri",
    )


# Invalid service configuration
def test_authorization_code_flow_with_invalid_response_type(client: TestClient) -> None:
    data_with_invalid_client_id = {
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "invalid_response_type",
        "scope": "API openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert query["error"][0] == "unsupported_response_type"


# Invalid user response
def test_authorization_code_flow_with_invalid_user_credentials(
    client: TestClient,
) -> None:
    data_with_invalid_client_id = {
        "client_id": "AppAuthClientWithClientSecret",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "email@myecl.fr",
        "password": "other invalid password",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/login/?client_id=AppAuthClientWithClientSecret&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fdocs&scope=API+openid&state=azerty&credentials_error=True",
    )


# Valid user response
def test_authorization_code_flow_with_auth_client_restricting_allowed_groups_and_user_member_of_an_allowed_group(
    client: TestClient,
) -> None:
    # For an user that is a member of a required group #
    data_with_invalid_client_id = {
        "client_id": "RestrictingUsersGroupsAuthClient",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "email@etu.ec-lyon.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert (url.path, query["state"][0]) == ("/docs", "azerty")
    assert query["code"][0] != ""


def test_authorization_code_flow_with_auth_client_restricting_allowed_groups_and_user_not_member_of_an_allowed_group(
    client: TestClient,
) -> None:
    # For an user that is not a member of a required group #
    data_with_invalid_client_id = {
        "client_id": "RestrictingUsersGroupsAuthClient",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "external@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )
    assert response.status_code == 302

    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/error?message=User+account+type+is+not+allowed",
    )


def test_authorization_code_flow_with_auth_client_restricting_external_users_and_user_external(
    client: TestClient,
) -> None:
    # For an user that is not a member of a required group #
    data_with_invalid_client_id = {
        "client_id": "RalllyAuthClient",
        "client_secret": "secret",
        "redirect_uri": "http://127.0.0.1:8000/docs",
        "response_type": "code",
        "scope": "API openid",
        "state": "azerty",
        "email": "external@myecl.fr",
        "password": "azerty",
    }
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data_with_invalid_client_id,
        follow_redirects=False,
    )
    assert response.status_code == 302

    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/error?message=User+account+type+is+not+allowed",
    )


def test_token_introspection_unauthorized_for_auth_client_disallowing_introspection(
    client: TestClient,
):
    data = {
        "client_id": "BaseAuthClient",
        "client_secret": "secret",
        "token": access_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 401


def test_token_introspection_without_client_id(
    client: TestClient,
):
    data = {
        "client_secret": "secret",
        "token": access_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 401


def test_token_introspection_with_invalid_client_secret(
    client: TestClient,
):
    data = {
        "client_id": "BaseAuthClient",
        "client_secret": "invalid_secret",
        "token": access_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 401


def test_token_introspection_with_access_token(
    client: TestClient,
):
    data = {
        "client_id": "SynapseAuthClient",
        "client_secret": "secret",
        "token": access_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is True


def test_token_introspection_with_access_token_and_auth_in_header(
    client: TestClient,
):
    data = {
        "token": access_token,
    }
    client_id = "SynapseAuthClient"
    client_secret = "secret"
    basic_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    response = client.post(
        "/auth/introspect",
        data=data,
        headers={"Authorization": f"Basic {basic_header}"},
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is True


def test_token_introspection_with_an_expired_access_token(
    client: TestClient,
):
    expired_access_token = create_api_access_token(
        user,
        expires_delta=timedelta(seconds=-1),
    )
    data = {
        "client_id": "SynapseAuthClient",
        "client_secret": "secret",
        "token": expired_access_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is False


def test_token_introspection_with_invalid_refresh_token(
    client: TestClient,
):
    data = {
        "client_id": "SynapseAuthClient",
        "client_secret": "secret",
        "token": "InvalidRefreshToken",
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is False


def test_token_introspection_with_valid_refresh_token(
    client: TestClient,
):
    data = {
        "client_id": "SynapseAuthClient",
        "client_secret": "secret",
        "token": valid_refresh_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is True


def test_token_introspection_with_expired_refresh_token(
    client: TestClient,
):
    data = {
        "client_id": "SynapseAuthClient",
        "client_secret": "secret",
        "token": expired_refresh_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is False


def test_token_introspection_with_revoked_refresh_token(
    client: TestClient,
):
    data = {
        "client_id": "SynapseAuthClient",
        "client_secret": "secret",
        "token": revoked_refresh_token,
    }
    response = client.post(
        "/auth/introspect",
        data=data,
    )
    assert response.status_code == 200
    json = response.json()

    assert json["active"] is False


def test_get_jwks_uri(
    client: TestClient,
) -> None:
    response = client.get(
        "/oidc/authorization-flow/jwks_uri",
    )
    assert response.status_code == 200
    json = response.json()
    assert len(json["keys"]) >= 1


def test_get_oauth_configuration(
    client: TestClient,
) -> None:
    response = client.get(
        "/.well-known/oauth-authorization-server",
    )
    assert response.status_code == 200
    json = response.json()
    assert json["issuer"] == "http://127.0.0.1:8000"


def test_get_oidc_configuration(
    client: TestClient,
) -> None:
    response = client.get(
        "/.well-known/openid-configuration",
    )
    assert response.status_code == 200
    json = response.json()
    assert json["issuer"] == "http://127.0.0.1:8000"
