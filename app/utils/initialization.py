from sqlalchemy import select
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core import models_core
from app.core.config import Settings

# These utils are used at startup to run database initializations & migrations


def get_sync_db_engine(settings: Settings) -> Engine:
    """
    Create a synchronous database engine
    """
    if settings.SQLITE_DB:
        SQLALCHEMY_DATABASE_URL = f"sqlite:///./{settings.SQLITE_DB}"
    else:
        SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=settings.DATABASE_DEBUG)
    return engine


def get_all_module_visibility_membership_sync(
    db: Session,
):
    """
    Return the every module with their visibility
    """
    result = db.execute(select(models_core.ModuleVisibility))
    return result.unique().scalars().all()


def create_module_visibility_sync(
    module_visibility: models_core.ModuleVisibility,
    db: Session,
) -> models_core.ModuleVisibility:
    """
    Create a new module visibility in database and return it
    """
    db.add(module_visibility)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise
    else:
        return module_visibility


def get_group_by_id_sync(group_id: str, db: Session) -> models_core.CoreGroup | None:
    """
    Return group with id from database
    """
    result = db.execute(
        select(models_core.CoreGroup)
        .where(models_core.CoreGroup.id == group_id)
        .options(
            selectinload(models_core.CoreGroup.members),
        ),  # needed to load the members from the relationship
    )
    return result.scalars().first()


def create_group_sync(
    group: models_core.CoreGroup,
    db: Session,
) -> models_core.CoreGroup:
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
