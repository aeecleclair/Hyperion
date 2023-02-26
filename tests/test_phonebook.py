import uuid

from app.cruds import cruds_phonebook
from app.dependencies import get_settings
from app.main import app
from app.models import models_core, models_phonebook
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

user: models_core.CoreUser | None = None
CAA_user: models_core.CoreUser | None = None
association: models_phonebook.Association | None = None
role: models_phonebook.Role | None = None
member: models_phonebook.Member | None = None

settings = app.dependency_overrides.get(get_settings, get_settings)()


@app.on_event("startup")
async def startuptest():
    global user, association, role, member, CAA_user

    async with TestingSessionLocal() as db:
        user = await create_user_with_groups([GroupType.student], db=db)
        CAA_user = await create_user_with_groups([GroupType.CAA], db=db)

        association = models_phonebook.Association(
            id=str(uuid.uuid4()),
            name="Association1",
        )
        association2 = models_phonebook.Association(
            id="b5c99d5b-bc48-4f9c-9e41-c69049d89bf3",
            name="Association2",
        )

        role = models_phonebook.Role(id=str(uuid.uuid4()), name="Role1")
        role2 = models_phonebook.Role(id=str(uuid.uuid4()), name="Role2")

        user.name = "Nom"
        user.firstname = "Prénom"
        user.nickname = "Pseudo"
        user.id = str(uuid.uuid4())
        user.email = "test.rate@ecl21.ec-lyon.fr"

        member = models_phonebook.Member(
            user_id=user.id,
            role_id=role.id,
            mandate_year=2021,
            member_id=str(uuid.uuid4()),
            association_id=association.id,
        )

        db.add(association)
        db.add(role)
        db.add(member)
        await db.commit()


def test_create_association_by_student():
    token = create_api_access_token(user)

    response = client.post(
        "/phonebook/associations/?name=Fablab",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_create_association_by_CAA():
    token = create_api_access_token(CAA_user)

    response = client.post(
        "/phonebook/associations/?name=Fablab",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_update_association():
    token = create_api_access_token(CAA_user)
    response = client.patch(
        "/phonebook/associations/?name=Usine à Gaz",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_delete_association():
    token = create_api_access_token(CAA_user)

    response = client.delete(
        "/phonebook/associations/?id=b5c99d5b-bc48-4f9c-9e41-c69049d89bf3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_member():
    token = create_api_access_token(CAA_user)

    response = client.post(
        "/phonebook/members/?association_id=b5c99d5b-bc48-4f9c-9e41-c69049d89bf3&mandate_year=2022&role_id=10&user_id=15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

def test_update_member():
    token = create_api_access_token(CAA_user)
    
    response = client.patch(
        "/phonebook/members/?association_id=b5c99d5b-bc48-4f9c-9e41-c69049d89bf3&mandate_year=2020&role_id=15&user_id=10",

def test_request_by_person():
    token = create_api_access_token(user)

    response = client.get(
        "/phonebook/research/?query=Nom&query_type=person",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(response.json())
    assert response.status_code == 200
