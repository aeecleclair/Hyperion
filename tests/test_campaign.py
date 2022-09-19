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
student_user: models_core.CoreUser | None = None


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global admin_user, student_user

    async with TestingSessionLocal() as db:
        admin_user = await create_user_with_groups([GroupType.admin], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        await db.commit()


def test_get_get_sections():
    token = create_api_access_token(student_user)
    response = client.get(
        "/campaign/sections", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
