from tests.commons import client
from app.main import app
from app.models import models_core
from tests.commons import TestingSessionLocal

id_eclair = "8aab79e7-1e15-456d-b6e2-11e4e9f77e4f"


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:
        eclair = models_core.CoreGroup(
            id=id_eclair,
            name="eclair",
            description="Les meilleurs",
        )
        db.add(eclair)
        await db.commit()


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass


def test_get_group_by_id():
    response = client.get(f"/groups/{id_eclair}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "eclair"


def test_post_group():
    response = client.post(
        "/groups/",
        json={
            "name": "bde",
            "description": "head of students associations",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "bde"
    assert data["description"] == "head of students associations"


def test_patch_group():
    response = client.patch(
        "/groups/{id_eclair}".format(id_eclair=id_eclair),
        json={"description": "The best"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "eclair"
    assert data["description"] == "The best"


def test_delete_group():
    response = client.delete(f"/groups/{id_eclair}")
    assert response.status_code == 204
