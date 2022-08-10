from app.main import app
from app.models import models_amap
from app.schemas import schemas_amap
from tests.commons import TestingSessionLocal, client


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:
        test1 = models_amap.Product(
            id="test1", name="Test1", price=0.99, category="Tests"
        )
        test2 = models_amap.Product(
            id="test2", name="Test2", price=12, category="Tests"
        )

        db.add(test1)
        db.add(test2)
        await db.commit()


def test_products():
    response = client.get("/amap/products")
    assert response.status_code == 200
    response = client.post(
        "/amap/products",
        schemas_amap.ProductSimple(name="Test2", price=0.01, category="Tests"),
    )
    assert response.status_code == 201
