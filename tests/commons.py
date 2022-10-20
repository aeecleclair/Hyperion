import logging
import uuid
from functools import lru_cache
from typing import AsyncGenerator

import redis
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core import security
from app.core.config import Settings
from app.cruds import cruds_groups, cruds_users
from app.database import Base
from app.dependencies import get_db, get_redis_client, get_settings
from app.main import app
from app.models import models_core
from app.schemas import schemas_auth
from app.utils.redis import connect, disconnect
from app.utils.types.floors_type import FloorsType
from app.utils.types.groups_type import GroupType

settings = Settings(
    _env_file=".env.test"
)  # Load the test's settings to configure the database
if settings.SQLITE_DB:
    SQLALCHEMY_DATABASE_URL = (
        "sqlite+aiosqlite:///./test.db"  # Connect to the test's database
    )
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"


engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)  # Create a session for testing purposes


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db function to use the testing session"""

    async with TestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@lru_cache()
def override_get_settings() -> Settings:
    """Override the get_settings function to use the testing session"""
    return Settings(_env_file=".env.test")


redis_client = None

hyperion_error_logger = logging.getLogger("hyperion.error")


def override_get_redis_client(
    settings=None, activate=False, deactivate=False
) -> (
    redis.Redis | None | bool
):  # As we don't want the limiter to be activated, except during the designed test, we add an "activate"/"deactivate" option
    """Override the get_redis_client function to use the testing session"""
    global redis_client
    if activate:
        if settings.REDIS_HOST != "":
            try:
                redis_client = connect(settings)
            except redis.exceptions.ConnectionError:
                hyperion_error_logger.warning(
                    "Redis connection error: Check the Redis configuration  or the Redis server"
                )
    elif deactivate:
        if type(redis_client) == redis.Redis:
            disconnect(redis_client)
        redis_client = None
    return redis_client


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_settings] = override_get_settings
app.dependency_overrides[get_redis_client] = override_get_redis_client


@app.on_event("startup")
async def commonstartuptest():
    # create db tables in test.db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Add the necessary groups for account types
    description = "Group type"
    account_types = [
        models_core.CoreGroup(id=id, name=id.name, description=description)
        for id in GroupType
    ]
    async with TestingSessionLocal() as db:
        try:
            db.add_all(account_types)
            await db.commit()
        except IntegrityError:
            await db.rollback()


client = TestClient(app)  # Create a client to execute tests


async def create_user_with_groups(
    groups: list[GroupType],
    db: AsyncSession,
) -> models_core.CoreUser:
    """
    Add a dummy user to the database
    The user will be named with its user_id. Email and password will both be its user_id

    The user will be added to provided `groups`
    """
    user_id = str(uuid.uuid4())

    password_hash = security.get_password_hash(user_id)

    user = models_core.CoreUser(
        id=user_id,
        email=user_id,
        password_hash=password_hash,
        name=user_id,
        firstname=user_id,
        floor=FloorsType.Autre,
    )

    await cruds_users.create_user(db=db, user=user)

    for group in groups:
        await cruds_groups.create_membership(
            db=db,
            membership=models_core.CoreMembership(
                group_id=group.value,
                user_id=user_id,
            ),
        )

    return user


def create_api_access_token(user: models_core.CoreUser):
    """
    Create a JWT access token for the `user` with the scope `API`
    """
    # Unfortunately, FastAPI does not support using dependency in startup events.
    # We reproduce FastAPI logic to access settings. See https://github.com/tiangolo/fastapi/issues/425#issuecomment-954963966
    settings = app.dependency_overrides.get(get_settings, get_settings)()

    access_token_data = schemas_auth.TokenData(sub=user.id, scopes="API")
    token = security.create_access_token(data=access_token_data, settings=settings)

    return token
