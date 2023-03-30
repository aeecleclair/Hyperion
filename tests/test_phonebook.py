import uuid


from app.main import app
from app.models import models_phonebook, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

membership: models_phonebook.Membership | None = None
association: models_phonebook.Association | None = None
members: models_phonebook.Members | None = None
role: models_phonebook.Role | None = None
phonebook_user_caa: models_core.CoreUser | None = None
phonebook_user_simple: models_core.CoreUser | None = None
token_caa: str = ""
token_simple: str = ""

@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global phonebook_user_caa
    async with TestingSessionLocal() as db:
        phonebook_user_caa = await create_user_with_groups([GroupType.CAA], db=db)
        await db.commit()

    global token_caa
    token_caa = create_api_access_token(phonebook_user_caa)

    global phonebook_user_simple
    async with TestingSessionLocal() as db:
        phonebook_user_simple = await create_user_with_groups([GroupType.student],db=db)
        await db.commit()

    global token_simple
    token_simple = create_api_access_token(phonebook_user_simple)

    global role
    async with TestingSessionLocal() as db:
        role = models_phonebook.Role(id=str(uuid.uuid4()), name="VP Emprunts")

    global membership
    async with TestingSessionLocal() as db:
        membership = models_phonebook.Membership(
            user_id=str(uuid.uuid4())
            association_id=association.id,
            role_id=role.id
        )

    global association
    async with TestingSessionLocal() as db:
        association = models_phonebook.Association(
            id=str(uuid.uuid4()),
            type="Section",
            name="ÉCLAIR",
            membership=[membership]
            )