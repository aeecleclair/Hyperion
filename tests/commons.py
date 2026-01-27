import logging
import uuid
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

from app import dependencies
from app.core.auth import schemas_auth
from app.core.groups import cruds_groups, models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfig, HelloAssoConfigName
from app.core.permissions import cruds_permissions, schemas_permissions
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users, models_users, schemas_users
from app.core.utils import security
from app.core.utils.config import Settings
from app.types import core_data
from app.types.scheduler import OfflineScheduler
from app.types.sqlalchemy import Base, SessionLocalType
from app.utils.communication.notifications import NotificationManager
from app.utils.state import (
    GlobalState,
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


async def override_init_state(
    app: FastAPI,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> None:
    """
    Initialize the state of the application. This dependency should be used at the start of the application lifespan.
    """

    engine = init_test_engine(settings=settings)

    SessionLocal = init_test_SessionLocal(engine=engine)

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

    payment_tools = init_test_payment_tools()

    mail_templates = init_mail_templates(settings=settings)

    dependencies.GLOBAL_STATE = GlobalState(
        engine=engine,
        SessionLocal=SessionLocal,
        redis_client=redis_client,
        scheduler=scheduler,
        ws_manager=ws_manager,
        notification_manager=notification_manager,
        payment_tools=payment_tools,
        mail_templates=mail_templates,
    )


def create_test_settings(**kwargs) -> Settings:
    """Override the get_settings function to use the testing session"""

    return Settings(
        _env_file="./tests/.env.test",
        _yaml_file="./tests/config.test.yaml",
        USE_NULL_POOL=True,
        **kwargs,
    )


# We use a global `SETTINGS` and a global `TestingSessionLocal` object
# to be able to access it from tests
SETTINGS: Settings
TestingSessionLocal: SessionLocalType


@lru_cache
def override_get_settings() -> Settings:
    return SETTINGS  # noqa: F821


def get_TestingSessionLocal() -> SessionLocalType:
    return TestingSessionLocal


def get_database_sync_url() -> str:
    settings = override_get_settings()
    if settings.SQLITE_DB:
        return f"sqlite:///./{settings.SQLITE_DB}"
    return f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"


def init_test_engine(settings: Settings) -> AsyncEngine:
    """
    Return the (asynchronous) database engine, if the engine doesn't exit yet it will create one based on the settings
    """
    # Connect to the test's database
    if settings.SQLITE_DB:
        SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///./{settings.SQLITE_DB}"
    else:
        SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

    return create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=settings.DATABASE_DEBUG,
        # We need to use NullPool to run tests with Postgresql
        # See https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
        poolclass=NullPool,
    )


def init_test_SessionLocal(engine: AsyncEngine) -> SessionLocalType:
    global TestingSessionLocal
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return TestingSessionLocal


def init_test_payment_tools() -> dict[HelloAssoConfigName, PaymentTool]:
    payment_tools: dict[HelloAssoConfigName, PaymentTool] = {}
    for helloasso_config_name in HelloAssoConfigName:
        payment_tools[helloasso_config_name] = MockedPaymentTool()

    return payment_tools


hyperion_error_logger = logging.getLogger("hyperion.error")

TEST_PASSWORD_HASH = security.get_password_hash(get_random_string())


async def add_account_type_permission(
    permission: str,
    account_type: AccountType,
):
    async with TestingSessionLocal() as db:
        try:
            await cruds_permissions.create_account_type_permission(
                db=db,
                permission=schemas_permissions.CoreAccountTypePermission(
                    permission_name=permission,
                    account_type=account_type,
                ),
            )
            await db.commit()
        except Exception as error:
            await db.rollback()
            raise FailedToAddObjectToDB from error
        finally:
            await db.close()


async def create_groups_with_permissions(
    permissions: list[str],
    group_name: str,
) -> models_groups.CoreGroup:
    """
    Add a dummy group to the database
    Group property will be randomly generated if not provided

    The group will be added to provided `permissions`
    """

    group_id = str(uuid.uuid4())

    group = models_groups.CoreGroup(
        id=group_id,
        name=group_name,
        description=None,
    )

    async with TestingSessionLocal() as db:
        try:
            await cruds_groups.create_group(db=db, group=group)

            for permission in permissions:
                await cruds_permissions.create_group_permission(
                    db=db,
                    permission=schemas_permissions.CoreGroupPermission(
                        permission_name=permission,
                        group_id=group_id,
                    ),
                )
            await db.commit()
        except Exception as error:
            await db.rollback()
            raise FailedToAddObjectToDB from error
        finally:
            await db.close()
    async with TestingSessionLocal() as db:
        group_db = await cruds_groups.get_group_by_id(db, group_id)
        await db.close()

    return group_db  # type: ignore # (group_db can't be None)  # noqa: PGH003


async def create_user_with_groups(
    groups: list[GroupType | str],
    account_type: AccountType = AccountType.student,
    school_id: SchoolType | uuid.UUID = SchoolType.centrale_lyon,
    user_id: str | None = None,
    email: str | None = None,
    password: str | None = None,
    name: str | None = None,
    firstname: str | None = None,
    floor: str | None = None,
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
                        group_id=group.value if isinstance(group, GroupType) else group,
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
        settings=override_get_settings(),
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


mocked_checkout_id: uuid.UUID = uuid.UUID("81c9ad91-f415-494a-96ad-87bf647df82c")


class MockedPaymentTool(PaymentTool):
    def __init__(
        self,
    ):
        self.payment_tool = PaymentTool(
            config=HelloAssoConfig(
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
        exist = await cruds_payment.get_checkout_by_id(mocked_checkout_id, db)
        if exist is None:
            checkout_model = models_payment.Checkout(
                id=mocked_checkout_id,
                module=module,
                name=checkout_name,
                amount=checkout_amount,
                hello_asso_checkout_id=123,
                secret="checkoutsecret",
            )
            await cruds_payment.create_checkout(db, checkout_model)

        return schemas_payment.Checkout(
            id=mocked_checkout_id,
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
