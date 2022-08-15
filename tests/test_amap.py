from app.main import app
from app.models import models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

amap_user: models_core.CoreUser | None = None


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global amap_user
    async with TestingSessionLocal() as db:
        amap_user = await create_user_with_groups([GroupType.amap], db=db)
        await db.commit()


def test_get_rights():
    token = create_api_access_token(amap_user)
    response = client.get(
        "/amap/rights",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
