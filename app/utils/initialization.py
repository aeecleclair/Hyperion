import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import redis
from pydantic import ValidationError
from sqlalchemy import Connection, MetaData, delete, select
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.core_endpoints import models_core
from app.core.groups import models_groups
from app.core.schools import models_schools
from app.core.utils.config import Settings
from app.types import core_data
from app.types.exceptions import (
    CoreDataNotFoundError,
    WaitUnlockMissingUnlockKey,
)
from app.types.sqlalchemy import Base

# These utils are used at startup to run database initializations & migrations


def get_sync_db_engine(settings: Settings) -> Engine:
    """
    Create a synchronous database engine
    """
    if settings.SQLITE_DB:
        SQLALCHEMY_DATABASE_URL = f"sqlite:///./{settings.SQLITE_DB}"
    else:
        SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

    return create_engine(SQLALCHEMY_DATABASE_URL, echo=settings.DATABASE_DEBUG)


def get_all_module_group_visibility_membership_sync(
    db: Session,
):
    """
    Return the every module with their visibility
    """
    result = db.execute(select(models_core.ModuleGroupVisibility))
    return result.unique().scalars().all()


def get_all_module_account_type_visibility_membership_sync(
    db: Session,
):
    """
    Return the every module with their visibility
    """
    result = db.execute(select(models_core.ModuleAccountTypeVisibility))
    return result.unique().scalars().all()


def create_module_group_visibility_sync(
    module_visibility: models_core.ModuleGroupVisibility,
    db: Session,
) -> models_core.ModuleGroupVisibility:
    """
    Create a new module visibility in database and return it
    """
    db.add(module_visibility)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    else:
        return module_visibility


def create_module_account_type_visibility_sync(
    module_visibility: models_core.ModuleAccountTypeVisibility,
    db: Session,
) -> models_core.ModuleAccountTypeVisibility:
    """
    Create a new module visibility in database and return it
    """
    db.add(module_visibility)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    else:
        return module_visibility


def get_group_by_id_sync(group_id: str, db: Session) -> models_groups.CoreGroup | None:
    """
    Return group with id from database
    """
    result = db.execute(
        select(models_groups.CoreGroup).where(
            models_groups.CoreGroup.id == group_id,
        ),  # needed to load the members from the relationship
    )
    return result.scalars().first()


def create_group_sync(
    group: models_groups.CoreGroup,
    db: Session,
) -> models_groups.CoreGroup:
    """
    Create a new group in database and return it
    """
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    else:
        return group


def get_core_data_crud_sync(schema: str, db: Session) -> models_core.CoreData | None:
    """
    Return core data with schema from database
    """
    result = db.execute(
        select(models_core.CoreData).where(models_core.CoreData.schema == schema),
    )
    return result.scalars().first()


def set_core_data_crud_sync(
    core_data: models_core.CoreData,
    db: Session,
) -> models_core.CoreData:
    """
    Set core data in database and return it
    """
    db.add(core_data)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    else:
        return core_data


def get_school_by_id_sync(
    school_id: str,
    db: Session,
) -> models_schools.CoreSchool | None:
    """
    Return group with id from database
    """
    result = db.execute(
        select(models_schools.CoreSchool).where(
            models_schools.CoreSchool.id == school_id,
        ),
    )
    return result.scalars().first()


def create_school_sync(
    school: models_schools.CoreSchool,
    db: Session,
) -> models_schools.CoreSchool:
    """
    Create a new group in database and return it
    """
    db.add(school)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    else:
        return school


def delete_core_data_crud_sync(schema: str, db: Session) -> None:
    """
    Delete core data with schema from database
    """
    db.execute(
        delete(models_core.CoreData).where(models_core.CoreData.schema == schema),
    )
    db.commit()


CoreDataClass = TypeVar("CoreDataClass", bound=core_data.BaseCoreData)


def get_core_data_sync(
    core_data_class: type[CoreDataClass],
    db: Session,
) -> CoreDataClass:
    """
    Access the core data stored in the database, using the name of the class `core_data_class`.
    If the core data does not exist, it returns a new instance of `core_data_class`, including its default values, or raise a CoreDataNotFoundError.
    `core_data_class` should be a class extending `BaseCoreData`.

    This method should be called using the class object, and not an instance of the class:
    ```python
    await get_core_data(ExempleCoreData, db)
    ```

    See `BaseCoreData` for more information.
    """
    # `core_data_class` contains the class object, and not an instance of the class.
    # We can call `core_data_class.__name__` to get the name of the class
    schema_name = core_data_class.__name__
    core_data_model = get_core_data_crud_sync(
        schema=schema_name,
        db=db,
    )

    if core_data_model is None:
        # Return default values
        try:
            return core_data_class()
        except ValidationError as error:
            # If creating a new instance of the class raises a ValidationError, it means that the class does not have default values
            # We should then raise an exception
            raise CoreDataNotFoundError() from error

    return core_data_class.model_validate_json(
        core_data_model.data,
        strict=True,
    )


def set_core_data_sync(
    core_data: core_data.BaseCoreData,
    db: Session,
) -> None:
    """
    Set the core data in the database using the name of the class `core_data` is an instance of.

    This method should be called using an instance of a class extending `BaseCoreData`:
    ```python
    example_core_data = ExempleCoreData()
    await get_core_data(example_core_data, db)
    ```

    See `BaseCoreData` for more information.
    """
    # `core_data` contains an instance of the class.
    # We call `core_data_class.__class__.__name__` to get the name of the class
    schema_name = core_data.__class__.__name__

    core_data_model = models_core.CoreData(
        schema=schema_name,
        data=core_data.model_dump_json(),
    )

    # We want to remove the old data
    delete_core_data_crud_sync(schema=schema_name, db=db)
    # And then add the new one
    set_core_data_crud_sync(core_data=core_data_model, db=db)


def drop_db_sync(conn: Connection):
    """
    Drop all tables in the database
    """
    # All tables should be dropped, including the alembic_version table
    # or Hyperion will think that the database is up to date and will not initialize it
    # when running tests a second time.
    # To let SQLAlchemy drop the alembic_version table, we created a AlembicVersion model.

    # `Base.metadata.drop_all(conn)` is only able to drop tables that are defined in models
    # This means that if a model is deleted, its table will never be dropped by `Base.metadata.drop_all(conn)`

    # Thus we construct a metadata object that reflects the database instead of only using models
    my_metadata: MetaData = MetaData(schema=Base.metadata.schema)
    my_metadata.reflect(bind=conn, resolve_fks=False)
    my_metadata.drop_all(bind=conn)


async def use_lock_for_workers(
    func: Callable[..., Coroutine[Any, Any, Any]] | Callable[..., Any],
    params: list[Any],
    key: str,
    redis_client: redis.Redis,
    logger: logging.Logger,
    wait_unlock: bool = False,
    unlock_key: str | None = None,
):
    if not wait_unlock:
        if redis_client.setnx(key, "1"):
            logger.info(f"Running {func.__name__}")
            result = func(*params)
            if isinstance(result, Coroutine):
                result = await result
            redis_client.expire(key, 20)
            return result
        return

    elif not unlock_key:
        raise WaitUnlockMissingUnlockKey()

    while redis_client.get(unlock_key) is None:
        if redis_client.setnx(key, "1"):
            logger.info(f"Running {func.__name__}")
            result = func(*params)
            if isinstance(result, Coroutine):
                result = await result
            redis_client.set(unlock_key, "1")
            redis_client.expire(unlock_key, 20)
            redis_client.expire(key, 20)
            return result

        else:
            logger.info(f"Waiting for {func.__name__} to finish")
            await asyncio.sleep(1)
