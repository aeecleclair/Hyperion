import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.amap import cruds_amap, models_amap, schemas_amap
from app.modules.amap.types_amap import DeliveryStatusType
from app.types.factory import Factory


class AmapFactory(Factory):
    depends_on = [CoreUsersFactory]

    @classmethod
    async def create_products(cls, db: AsyncSession):
        # Generates sample products
        products: dict[str, tuple[int, str]] = {
            "banane": (500, "Fruits"),
            "pomme": (600, "Fruits"),
            "poire": (400, "Fruits"),
            "kiwi": (300, "Fruits"),
            "orange": (200, "Fruits"),
            "carotte": (100, "Légumes"),
            "tomate": (200, "Légumes"),
        }

        for product_name, product_data in products.items():
            await cruds_amap.create_product(
                db=db,
                product=models_amap.Product(
                    id=str(uuid.uuid4()),
                    name=product_name,
                    price=product_data[0],
                    category=product_data[1],
                ),
            )

    @classmethod
    async def create_delivery(cls, db: AsyncSession):
        products = await cruds_amap.get_products(db=db)

        await cruds_amap.create_delivery(
            db=db,
            delivery=schemas_amap.DeliveryComplete(
                id=str(uuid.uuid4()),
                name="Première livraison",
                status=DeliveryStatusType.orderable,
                delivery_date=(datetime.now(UTC) + timedelta(days=8)).date(),
                products_ids=[product.id for product in products],
            ),
        )

        await cruds_amap.create_delivery(
            db=db,
            delivery=schemas_amap.DeliveryComplete(
                id=str(uuid.uuid4()),
                name="Deuxième livraison",
                status=DeliveryStatusType.orderable,
                delivery_date=(datetime.now(UTC) + timedelta(days=1)).date(),
                products_ids=[product.id for product in products],
            ),
        )

    @classmethod
    async def create_cash_of_user(cls, db: AsyncSession):
        await cruds_amap.create_cash_of_user(
            db=db,
            cash=models_amap.Cash(
                user_id=CoreUsersFactory.demo_users_id[0],
                balance=10000,
            ),
        )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.create_products(db)
        await cls.create_delivery(db)
        await cls.create_cash_of_user(db)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_amap.get_products(db=db)) == 0
