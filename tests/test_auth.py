import base64
import json
from urllib.parse import parse_qs, urlparse

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from tests.commons import (
    client,
    create_user_with_groups,
)

user: models_core.CoreUser
external_user: models_core.CoreUser
ecl_user: models_core.CoreUser


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
        groups=[GroupType.student],
        email="email@etu.ec-lyon.fr",
        password="azerty",
    )

    global external_user
    external_user = await create_user_with_groups(
        groups=[],
        email="external@myecl.fr",
        password="azerty",
        external=True,
    )


def test_simple_token():
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


def test_authorization_code_flow_PKCE() -> None:
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


def test_authorization_code_flow_secret() -> None:
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


def test_get_user_info() -> None:
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

    global user
    assert json["name"] == user.firstname


def test_get_user_info_in_id_token() -> None:
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

    global user
    assert json_payload["email"] == user.email


# Invalid service configuration
def test_authorization_code_flow_with_invalid_client_id() -> None:
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
    assert response.status_code == 422
    json = response.json()
    assert json["detail"] == "Invalid client_id"


# Invalid service configuration
def test_authorization_code_flow_with_invalid_redirect_uri() -> None:
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
    assert response.status_code == 422
    json = response.json()
    assert json["detail"] == "Mismatching redirect_uri"


# Invalid service configuration
def test_authorization_code_flow_with_invalid_response_type() -> None:
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
def test_authorization_code_flow_with_invalid_user_credentials() -> None:
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
    assert response.status_code != 302


# Valid user response
def test_authorization_code_flow_with_auth_client_restricting_allowed_groups_and_user_member_of_an_allowed_group() -> (
    None
):
    # For an user that is a member of a required group #
    data_with_invalid_client_id = {
        "client_id": "AcceptingOnlyECLUsersAuthClient",
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


def test_authorization_code_flow_with_auth_client_restricting_allowed_groups_and_user_not_member_of_an_allowed_group() -> (
    None
):
    # For an user that is not a member of a required group #
    data_with_invalid_client_id = {
        "client_id": "AcceptingOnlyECLUsersAuthClient",
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

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert query["error"][0] == "consent_required"


def test_authorization_code_flow_with_auth_client_restricting_external_users_and_user_external() -> (
    None
):
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

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert query["error"][0] == "consent_required"
