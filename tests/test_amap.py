from app.main import app
from app.models import models_amap
from tests.commons import TestingSessionLocal, client


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:
        test1 = models_amap.Product(
            id="test1", name="Test1", price=0.99, category="Tests"
        )

        db.add(test1)
        await db.commit()


def test_products():
    response = client.get("/amap/products")
    assert response.status_code == 200
