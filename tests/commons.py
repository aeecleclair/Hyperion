import logging
import uuid
from collections.abc import Callable
from datetime import timedelta
from functools import lru_cache

from fastapi import FastAPI
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.auth import schemas_auth
from app.core.groups import cruds_groups, models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfig, HelloAssoConfigName
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users, models_users, schemas_users
from app.core.utils import security
from app.core.utils.config import Settings
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.types import core_data
from app.types.floors_type import FloorsType
from app.types.scheduler import OfflineScheduler
from app.types.sqlalchemy import Base
from app.utils.communication.notifications import NotificationManager
from app.utils.state import (
    LifespanState,
    init_mail_templates,
    init_redis_client,
    init_websocket_connection_manager,
)
from app.utils.tools import (
    get_random_string,
    set_core_data,
)


class FailedToAddObjectToDB(Exception):
    """Exception raised when an object cannot be added to the database."""


async def override_init_app_state(
    app: FastAPI,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> LifespanState:
    """
    Initialize the state of the application. This dependency should be used at the start of the application lifespan.
    """
    engine = init_test_engine()

    SessionLocal = init_test_SessionLocal()

    redis_client = init_redis_client(
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    # Even if we have a Redis client, we still want to use the OfflineScheduler for tests
    # as tests are not able to run tasks in the future. The event loop of the test may not be running long enough
    # to execute the tasks.
    scheduler = OfflineScheduler()

    ws_manager = await init_websocket_connection_manager(
        settings=settings,
    )

    notification_manager = NotificationManager(settings=settings)

    drive_file_manager = DriveFileManager()

    payment_tools = init_test_payment_tools()

    mail_templates = init_mail_templates(settings=settings)

    return LifespanState(
        engine=engine,
        SessionLocal=SessionLocal,
        redis_client=redis_client,
        scheduler=scheduler,
        ws_manager=ws_manager,
        notification_manager=notification_manager,
        drive_file_manager=drive_file_manager,
        payment_tools=payment_tools,
        mail_templates=mail_templates,
    )


@lru_cache
def override_get_settings() -> Settings:
    """Override the get_settings function to use the testing session"""

    return Settings(
        _env_file="./tests/.env.test",
        _yaml_file="./tests/config.test.yaml",
    )


settings = override_get_settings()


# Connect to the test's database
if settings.SQLITE_DB:
    SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///./{settings.SQLITE_DB}"
    SQLALCHEMY_DATABASE_URL_SYNC = f"sqlite:///./{settings.SQLITE_DB}"
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"
    SQLALCHEMY_DATABASE_URL_SYNC = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"


engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.DATABASE_DEBUG,
    # We need to use NullPool to run tests with Postgresql
    # See https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
    poolclass=NullPool,
)

TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def init_test_engine() -> AsyncEngine:
    """
    Return the (asynchronous) database engine, if the engine doesn't exit yet it will create one based on the settings
    """

    return engine


def init_test_SessionLocal() -> Callable[[], AsyncSession]:
    return TestingSessionLocal


def init_test_payment_tools() -> dict[HelloAssoConfigName, PaymentTool]:
    payment_tools: dict[HelloAssoConfigName, PaymentTool] = {}
    for helloasso_config_name in HelloAssoConfigName:
        payment_tools[helloasso_config_name] = MockedPaymentTool()

    return payment_tools


# Create a session for testing purposes
TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


hyperion_error_logger = logging.getLogger("hyperion.error")

TEST_PASSWORD_HASH = security.get_password_hash(get_random_string())


async def create_user_with_groups(
    groups: list[GroupType],
    account_type: AccountType = AccountType.student,
    school_id: SchoolType | uuid.UUID = SchoolType.centrale_lyon,
    user_id: str | None = None,
    email: str | None = None,
    password: str | None = None,
    name: str | None = None,
    firstname: str | None = None,
    floor: FloorsType | None = None,
    nickname: str | None = None,
) -> models_users.CoreUser:
    """
    Add a dummy user to the database
    User property will be randomly generated if not provided

    The user will be added to provided `groups`
    """

    user_id = user_id or str(uuid.uuid4())
    password_hash = (
        security.get_password_hash(password) if password else TEST_PASSWORD_HASH
    )
    school_id = school_id.value if isinstance(school_id, SchoolType) else school_id

    user = models_users.CoreUser(
        id=user_id,
        email=email or (get_random_string() + "@etu.ec-lyon.fr"),
        school_id=school_id,
        password_hash=password_hash,
        name=name or get_random_string(),
        firstname=firstname or get_random_string(),
        nickname=nickname,
        floor=floor,
        account_type=account_type,
        birthday=None,
        promo=None,
        phone=None,
        created_on=None,
    )

    async with TestingSessionLocal() as db:
        try:
            await cruds_users.create_user(db=db, user=user)

            for group in groups:
                await cruds_groups.create_membership(
                    db=db,
                    membership=models_groups.CoreMembership(
                        group_id=group.value,
                        user_id=user_id,
                        description=None,
                    ),
                )
            await db.commit()
        except Exception as error:
            await db.rollback()
            raise FailedToAddObjectToDB from error
        finally:
            await db.close()

    async with TestingSessionLocal() as db:
        user_db = await cruds_users.get_user_by_id(db, user_id)
        assert user_db is not None
        return user_db


def create_api_access_token(
    user: models_users.CoreUser,
    expires_delta: timedelta | None = None,
):
    """
    Create a JWT access token for the `user` with the scope `API`
    """

    access_token_data = schemas_auth.TokenData(sub=user.id, scopes="API")
    return security.create_access_token(
        data=access_token_data,
        settings=settings,
        expires_delta=expires_delta,
    )


async def add_object_to_db(db_object: Base) -> None:
    """
    Add an object to the database
    """
    async with TestingSessionLocal() as db:
        try:
            db.add(db_object)
            await db.commit()
        except Exception as error:
            await db.rollback()
            raise FailedToAddObjectToDB from error
        finally:
            await db.close()


async def add_coredata_to_db(
    core_data: core_data.BaseCoreData,
) -> None:
    """
    Add a CoreData object
    """
    async with TestingSessionLocal() as db:
        try:
            await set_core_data(core_data, db=db)
            await db.commit()
        except Exception as error:
            await db.rollback()
            raise FailedToAddObjectToDB from error
        finally:
            await db.close()


class MockedPaymentTool(PaymentTool):
    def __init__(
        self,
    ):
        self.payment_tool = PaymentTool(
            config=HelloAssoConfig(
                name=HelloAssoConfigName.CDR,
                helloasso_client_id="client",
                helloasso_client_secret="secret",
                helloasso_slug="test",
                redirection_uri="https://example.com/redirect",
            ),
            helloasso_api_base="https://api.helloasso.com/v5",
        )

    def is_payment_available(self) -> bool:
        return True

    async def init_checkout(
        self,
        module: str,
        checkout_amount: int,
        checkout_name: str,
        db: AsyncSession,
        payer_user: schemas_users.CoreUser | None = None,
        redirection_uri: str | None = None,
    ) -> schemas_payment.Checkout:
        checkout_id = uuid.UUID("81c9ad91-f415-494a-96ad-87bf647df82c")

        exist = await cruds_payment.get_checkout_by_id(checkout_id, db)
        if exist is None:
            checkout_model = models_payment.Checkout(
                id=checkout_id,
                module="cdr",
                name=checkout_name,
                amount=500,
                hello_asso_checkout_id=123,
                secret="checkoutsecret",
            )
            await cruds_payment.create_checkout(db, checkout_model)

        return schemas_payment.Checkout(
            id=checkout_id,
            payment_url="https://some.url.fr/checkout",
        )

    async def get_checkout(
        self,
        checkout_id: uuid.UUID,
        db: AsyncSession,
    ) -> schemas_payment.CheckoutComplete | None:
        return await self.payment_tool.get_checkout(
            checkout_id=checkout_id,
            db=db,
        )
