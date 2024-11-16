import datetime
import uuid
from typing import Annotated

from sqlalchemy import DateTime, types
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, mapped_column
from sqlalchemy.types import TypeDecorator

from app.types.exceptions import MissingTZInfoInDatetimeError


class TZDateTime(TypeDecorator):
    """
    Custom SQLAlchemy type for storing timezone-aware timestamps as timezone-naive UTC timestamps.
    We use this custom type because sqlite doesn't support datetime with timezone
    See https://docs.sqlalchemy.org/en/20/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc
    """

    # Changing this type may break existing migrations. You may prefer to create a new version of the type instead.

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not value.tzinfo or value.tzinfo.utcoffset(value) is None:
                raise MissingTZInfoInDatetimeError()
            value = value.astimezone(datetime.UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=datetime.UTC)
        return value


# Pre-configured field type for UUID primary key (see https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#mapping-whole-column-declarations-to-python-types)
PrimaryKey = Annotated[uuid.UUID, mapped_column(primary_key=True)]


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for all models.

    The type map is overriden to use our custom datetime type (see https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#customizing-the-type-map)"""

    type_annotation_map = {
        bool: types.Boolean(),
        datetime.date: types.Date(),
        datetime.datetime: TZDateTime(),
        str: types.String(),
        uuid.UUID: types.Uuid(),
    }
