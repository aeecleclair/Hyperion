from app.main import app
from app.models import models_amap
from tests.commons import TestingSessionLocal


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:
        test1 = models_amap.Product(
            id="test1", name="Test1", price=0.99, category="Tests"
        )

        db.add(test1)
        await db.commit()
