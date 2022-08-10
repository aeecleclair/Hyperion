import uuid
from datetime import date
from urllib.parse import parse_qs, urlparse

from app.main import app
from app.models import models_core
from app.utils.examples import examples_auth
from tests.commons import TestingSessionLocal, client


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:
        user = models_core.CoreUser(
            id=str(uuid.uuid4()),
            email="email@myecl.fr",
            password_hash="$2b$13$laYmIYSoJxqtNSQZyXu7juK8LXkOAuA8y6FZ8vzEBpV.gq2sBOxTu",  # "azerty"
            name="Fabristpp",
            firstname="Antoine",
            nickname="Nickname",
            birthday=date.fromisoformat("2000-01-01"),
            floor="M16",
            created_on=date.fromisoformat("2000-01-01"),
        )
        db.add(user)
        await db.commit()


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
    code_challenge = "c2cf464b7901205c037cd821bc493b191943bdb5244a665e9fcab6478bf79415"  # hashlib.sha256("AntoineMonBelAntoine".encode()).hexdigest()
    data = examples_auth.example_AuthorizeValidation
    data["code_challenge"] = code_challenge
    response = client.post(
        "/auth/authorization-flow/authorize-validation",
        data=data,
    )
    assert response.status_code == 302

    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert (url.path, query["state"][0]) == ("/docs", "azerty")
    assert query["code"][0] is not None
    code = query["code"][0]

    data = examples_auth.example_TokenReq_access_token
    data["code"] = code
    data["code_verifier"] = code_verifier

    response = client.post("/auth/token", data=data)
    assert response.status_code == 200
    json = response.json()

    assert json["access_token"] is not None
    assert json["token_type"] == "bearer"
    assert json["expires_in"] == 1800
    assert json["refresh_token"] is not None

    refresh_token = json["refresh_token"]
    data = examples_auth.example_TokenReq_refresh_token
    data["refresh_token"] = refresh_token
    response = client.post("/auth/token", data=data)

    assert response.status_code == 200
    json = response.json()
    assert json["refresh_token"] is not None

    used_refresh_token = refresh_token
    valid_refresh_token = json["refresh_token"]

    data = examples_auth.example_TokenReq_refresh_token
    data["refresh_token"] = used_refresh_token
    data["client_secret"] = "secret"
    response = client.post("/auth/token", data=data)  # Try token reuse

    assert response.status_code == 400

    data = examples_auth.example_TokenReq_refresh_token
    data["refresh_token"] = valid_refresh_token
    data["client_secret"] = "secret"
    response = client.post(
        "/auth/token", data=data
    )  # Verify that the token has been revoked due to the reuse attempt

    assert response.status_code == 400
