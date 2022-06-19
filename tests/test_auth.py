import uuid
from datetime import date

from app.main import app
from app.models import models_core
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


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass


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

    # access_token validation
    response = client.get(
        "/users/", headers={"Authorization": f"Bearer {json['access_token']}"}
    )
    assert response.status_code != 401  # unauthorized
    assert response.status_code != 403  # forbidden
