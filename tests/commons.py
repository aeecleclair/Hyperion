import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from functools import lru_cache

import redis
from fastapi import Depends
from sqlalchemy import NullPool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import schemas_auth
from app.core.groups import cruds_groups, models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users, models_users, schemas_users
from app.core.utils import security
from app.core.utils.config import Settings
from app.dependencies import get_settings
from app.types.exceptions import RedisConnectionError
from app.types.floors_type import FloorsType
from app.types.scheduler import OfflineScheduler, Scheduler
from app.types.sqlalchemy import Base
from app.utils.redis import connect, disconnect
from app.utils.tools import (
    get_random_string,
)


@lru_cache
def override_get_settings() -> Settings:
    """Override the get_settings function to use the testing session"""
    return Settings(_env_file=".env.test", _env_file_encoding="utf-8")


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
)  # Create a session for testing purposes


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db function to use the testing session"""

    async with TestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


async def override_get_unsafe_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db function to use the testing session"""

    async with TestingSessionLocal() as db:
        yield db


# By default the redis client is deactivated
redis_client: redis.Redis | None | bool = False

hyperion_error_logger = logging.getLogger("hyperion.error")


def override_get_redis_client(
    settings: Settings = Depends(get_settings),
) -> (
    redis.Redis | None | bool
):  # As we don't want the limiter to be activated, except during the designed test, we add an "activate"/"deactivate" option
    """Override the get_redis_client function to use the testing session"""
    return redis_client


def change_redis_client_status(activated: bool) -> None:
    global redis_client
    if activated:
        if settings.REDIS_HOST != "":
            try:
                redis_client = connect(settings)
            except redis.exceptions.ConnectionError as err:
                raise RedisConnectionError() from err
    else:
        if isinstance(redis_client, redis.Redis):
            redis_client.flushdb()
            disconnect(redis_client)
        redis_client = False


def override_get_scheduler(
    settings: Settings = Depends(get_settings),
) -> Scheduler:  # As we don't want the limiter to be activated, except during the designed test, we add an "activate"/"deactivate" option
    """Override the get_redis_client function to use the testing session"""
    return OfflineScheduler()


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
    password_hash = security.get_password_hash(password or get_random_string())
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
        nickname=None,
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

        except IntegrityError:
            await db.rollback()
            raise
        finally:
            await db.close()
    async with TestingSessionLocal() as db:
        user_db = await cruds_users.get_user_by_id(db, user_id)
        await db.close()
    return user_db  # type: ignore # (user_db can't be None)


def create_api_access_token(
    user: models_users.CoreUser,
    expires_delta: timedelta | None = None,
):
    """
    Create a JWT access token for the `user` with the scope `API`
    """

    access_token_data = schemas_auth.TokenData(sub=user.id, scopes="API")
    token = security.create_access_token(
        data=access_token_data,
        settings=settings,
        expires_delta=expires_delta,
    )

    return token


async def add_object_to_db(db_object: Base) -> None:
    """
    Add an object to the database
    """
    async with TestingSessionLocal() as db:
        try:
            db.add(db_object)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise
        finally:
            await db.close()


class MockedPaymentTool:
    original_payment_tool: PaymentTool

    def __init__(self, settings: Settings):
        self.original_payment_tool = PaymentTool(settings)

    def is_payment_available(self) -> bool:
        return True

    async def init_checkout(
        self,
        module: str,
        helloasso_slug: str,
        checkout_amount: int,
        checkout_name: str,
        redirection_uri: str,
        db: AsyncSession,
        payer_user: schemas_users.CoreUser | None = None,
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
        return await self.original_payment_tool.get_checkout(checkout_id, db)


def override_get_payment_tool(
    settings: Settings = Depends(get_settings),
) -> MockedPaymentTool:
    return MockedPaymentTool(settings=settings)
