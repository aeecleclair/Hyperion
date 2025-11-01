import random
import uuid
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.myeclpay import cruds_myeclpay, models_myeclpay, schemas_myeclpay
from app.core.myeclpay.types_myeclpay import WalletType
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.types.factory import Factory

faker = Faker()

OTHER_STRUCTURES = 2


class MyPaymentFactory(Factory):
    depends_on = [CoreUsersFactory]

    demo_structures_id: list[uuid.UUID]
    other_structures_id: list[uuid.UUID]

    other_stores_id: list[list[uuid.UUID]] = []
    other_stores_wallet_id: list[list[uuid.UUID]] = []

    @classmethod
    async def create_structures(cls, db: AsyncSession):
        cls.demo_structures_id = [uuid.uuid4() for _ in CoreUsersFactory.demo_users_id]
        for i, user_id in enumerate(CoreUsersFactory.demo_users_id):
            await cruds_myeclpay.create_structure(
                schemas_myeclpay.StructureSimple(
                    id=uuid.uuid4(),
                    short_id="".join(faker.random_letters(3)).upper(),
                    name=CoreUsersFactory.demo_users[i].nickname,
                    manager_user_id=user_id,
                    siege_address_street=faker.street_address(),
                    siege_address_city=faker.city(),
                    siege_address_zipcode=faker.postcode(),
                    siege_address_country=faker.country(),
                    iban=faker.iban(),
                    bic="".join(faker.random_letters(11)).upper(),
                    creation=datetime.now(UTC),
                ),
                db,
            )
        cls.other_structures_id = [uuid.uuid4() for _ in range(OTHER_STRUCTURES)]
        for i, structure_id in enumerate(cls.other_structures_id):
            await cruds_myeclpay.create_structure(
                schemas_myeclpay.StructureSimple(
                    id=structure_id,
                    short_id="".join(faker.random_letters(3)).upper(),
                    name=faker.company(),
                    manager_user_id=CoreUsersFactory.other_users_id[i],
                    siege_address_street=faker.street_address(),
                    siege_address_city=faker.city(),
                    siege_address_zipcode=faker.postcode(),
                    siege_address_country=faker.country(),
                    iban=faker.iban(),
                    bic="".join(faker.random_letters(11)).upper(),
                    creation=datetime.now(UTC),
                ),
                db,
            )

    @classmethod
    async def create_other_structures_stores(cls, db: AsyncSession):
        for structure_id in cls.other_structures_id:
            structure_store_ids = []
            structure_wallet_ids = []
            for _ in range(random.randint(2, 4)):  # noqa: S311
                store_id = uuid.uuid4()
                wallet_id = uuid.uuid4()
                structure_store_ids.append(store_id)
                structure_wallet_ids.append(wallet_id)
                await cruds_myeclpay.create_wallet(
                    wallet_id=wallet_id,
                    wallet_type=WalletType.STORE,
                    balance=100000,
                    db=db,
                )
                await cruds_myeclpay.create_store(
                    models_myeclpay.Store(
                        id=store_id,
                        structure_id=structure_id,
                        name=faker.company(),
                        creation=datetime.now(UTC),
                        wallet_id=wallet_id,
                    ),
                    db,
                )
            cls.other_stores_id.append(structure_store_ids)
            cls.other_stores_wallet_id.append(structure_wallet_ids)

    @classmethod
    async def create_other_structures_invoices(cls, db: AsyncSession):
        for i, structure_id in enumerate(cls.other_structures_id):
            invoice_id = uuid.uuid4()
            await cruds_myeclpay.create_invoice(
                schemas_myeclpay.InvoiceInfo(
                    id=invoice_id,
                    structure_id=structure_id,
                    reference=faker.bothify(text="MYPAY2025???####"),
                    total=1000 * len(cls.other_stores_id[i]),
                    paid=False,
                    received=False,
                    start_date=datetime.now(UTC) - timedelta(days=30),
                    end_date=datetime.now(UTC),
                    creation=datetime.now(UTC),
                    details=[
                        schemas_myeclpay.InvoiceDetailBase(
                            invoice_id=invoice_id,
                            store_id=store_id,
                            total=1000,
                        )
                        for store_id in cls.other_stores_id[i]
                    ],
                ),
                db,
            )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls.create_structures(db)
        await cls.create_other_structures_stores(db)
        await cls.create_other_structures_invoices(db)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_myeclpay.get_structures(db=db)) == 0
