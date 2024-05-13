import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from functools import lru_cache

import pytest
import redis
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.app import get_application
from app.core import models_core, security
from app.core.auth import schemas_auth
from app.core.config import Settings
from app.core.groups import cruds_groups
from app.core.groups.groups_type import GroupType
from app.core.users import cruds_users
from app.dependencies import get_db, get_redis_client, get_settings
from app.types.floors_type import FloorsType
from app.types.sqlalchemy import Base
from app.utils.redis import connect, disconnect
from app.utils.tools import get_random_string


@lru_cache
def override_get_settings() -> Settings:
    """Override the get_settings function to use the testing session"""
    return Settings(_env_file=".env.test", _env_file_encoding="utf-8")  # type: ignore[call-arg] # See https://github.com/pydantic/pydantic/issues/3072, TODO: remove when fixes


settings = override_get_settings()

test_app = get_application(settings=settings, drop_db=True)  # Create the test's app

if settings.SQLITE_DB:
    SQLALCHEMY_DATABASE_URL = (
        f"sqlite+aiosqlite:///./{settings.SQLITE_DB}"  # Connect to the test's database
    )
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"


engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

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


# By default the redis client is deactivated
redis_client: redis.Redis | None | bool = False

hyperion_error_logger = logging.getLogger("hyperion.error")


def override_get_redis_client(
    settings: Settings = Depends(get_settings),
) -> (
    redis.Redis | None | bool
):  # As we don't want the limiter to be activated, except during the designed test, we add an "activate"/"deactivate" option
    """Override the get_redis_client function to use the testing session"""
    global redis_client
    return redis_client


def change_redis_client_status(activated: bool):
    global redis_client
    if activated:
        if settings.REDIS_HOST != "":
            try:
                redis_client = connect(settings)
            except redis.exceptions.ConnectionError as err:
                raise Exception("Connection to Redis failed") from err
    else:
        if isinstance(redis_client, redis.Redis):
            redis_client.flushdb()
            disconnect(redis_client)
        redis_client = False


test_app.dependency_overrides[get_db] = override_get_db
test_app.dependency_overrides[get_settings] = override_get_settings
test_app.dependency_overrides[get_redis_client] = override_get_redis_client


client = TestClient(test_app)  # Create a client to execute tests

with client:  # That syntax trigger the lifespan defined in main.py
    pass


# We need to redefine the event_loop (which is function scoped by default)
# to be able to use session scoped fixture (the function that initialize the db objects in each test file)
# See https://github.com/tortoise/tortoise-orm/issues/638#issuecomment-830124562
@pytest.fixture(scope="module")
def event_loop():
    """Overrides pytest default function scoped event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


async def create_user_with_groups(
    groups: list[GroupType],
    user_id: str | None = None,
    email: str | None = None,
    password: str | None = None,
    name: str | None = None,
    firstname: str | None = None,
    floor: FloorsType | None = None,
    external: bool = False,
) -> models_core.CoreUser:
    """
    Add a dummy user to the database
    User property will be randomly generated if not provided

    The user will be added to provided `groups`
    """

    user_id = user_id or str(uuid.uuid4())
    password_hash = security.get_password_hash(password or get_random_string())

    user = models_core.CoreUser(
        id=user_id,
        email=email or (get_random_string() + "@etu.ec-lyon.fr"),
        password_hash=password_hash,
        name=name or get_random_string(),
        firstname=firstname or get_random_string(),
        floor=floor,
        external=external,
    )

    async with TestingSessionLocal() as db:
        try:
            await cruds_users.create_user(db=db, user=user)

            for group in groups:
                await cruds_groups.create_membership(
                    db=db,
                    membership=models_core.CoreMembership(
                        group_id=group.value,
                        user_id=user_id,
                    ),
                )

        except IntegrityError as e:
            await db.rollback()
            raise e
        finally:
            await db.close()

    return user


def create_api_access_token(user: models_core.CoreUser):
    """
    Create a JWT access token for the `user` with the scope `API`
    """

    access_token_data = schemas_auth.TokenData(sub=user.id, scopes="API")
    token = security.create_access_token(data=access_token_data, settings=settings)

    return token


async def add_object_to_db(db_object: Base) -> None:
    """
    Add an object to the database
    """
    async with TestingSessionLocal() as db:
        try:
            db.add(db_object)
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
