from app.main import app
from app.models import models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser | None = None


id_eclair = "8aab79e7-1e15-456d-b6e2-11e4e9f77e4f"


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global admin_user

    async with TestingSessionLocal() as db:
        eclair = models_core.CoreGroup(
            id=id_eclair,
            name="eclair",
            description="Les meilleurs",
        )
        db.add(eclair)

        admin_user = await create_user_with_groups([GroupType.admin], db=db)

        await db.commit()


def test_get_group_by_id():
    token = create_api_access_token(admin_user)

    response = client.get(
        f"/groups/{id_eclair}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "eclair"
