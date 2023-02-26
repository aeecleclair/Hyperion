import uuid
from datetime import datetime

from app.dependencies import get_redis_client, get_settings
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
        role = models_phonebook.Role(id=str(uuid.uuid4()), name="Role1")

        user.name = "Nom"
        user.first_name = "Prénom"
        user.nickname = "Pseudo"

        member = models_phonebook.Member(
            user_id=user.id,
            role_id=str(uuid.uuid4()),
            mandate_year=2021,
            member_id=str(uuid.uuid4()),
            association_id=str(uuid.uuid4()),
        )

        db.add(association)
        db.add(role)
        db.add(member)
        await db.commit()


def test_request_by_person():
    token = create_api_access_token(user)

    response = client.get(
        "/phonebook/research/?query=Nom&query_type=person",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(response.json())
    assert response.status_code == 200
