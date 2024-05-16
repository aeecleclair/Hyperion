import base64
import json
import uuid
from datetime import date, datetime
from urllib.parse import parse_qs, urlparse

import pytest_asyncio

from app.core import models_core
from app.types.floors_type import FloorsType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import (
    add_object_to_db,
    client,
)

user: models_core.CoreUser


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global user
    user = models_core.CoreUser(
        id=str(uuid.uuid4()),
        email="email@myecl.fr",
        password_hash="$2b$13$laYmIYSoJxqtNSQZyXu7juK8LXkOAuA8y6FZ8vzEBpV.gq2sBOxTu",  # "azerty"
        name="Fabristpp",
        firstname="Antoine",
        nickname="Nickname",
        birthday=date.fromisoformat("2000-01-01"),
        floor=FloorsType.Autre,
        created_on=datetime.fromisoformat("2000-01-01T00:00:00Z"),
        external=False,
    )
    await add_object_to_db(user)


# def test_simple_token():
#    response = client.post(
#        "/auth/simple_token",
#        data={
#            "username": "email@myecl.fr",
#            "password": "azerty",
#        },
#    )
#    assert response.status_code == 200
#    json = response.json()
#
#    # Response data validation
#    assert "access_token" in json
#    assert json["token_type"] == "bearer"
#
#    # access_token validation
#    response = client.get(
#        "/users/", headers={"Authorization": f"Bearer {json['access_token']}"}
#    )
#    assert response.status_code != 401  # unauthorized
#    assert response.status_code != 403  # forbidden


def test_authorization_code_flow_PKCE():
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


def test_authorization_code_flow_secret():
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


def test_get_user_info():
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


def test_get_user_info_in_id_token():
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
