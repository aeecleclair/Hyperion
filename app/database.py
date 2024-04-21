"""File defining the Metadata."""

import datetime
import uuid
from typing import Annotated

from sqlalchemy import types
from sqlalchemy.orm import DeclarativeBase, mapped_column

from app.types.sqlalchemy import TZDateTime

# Pre-configured field type for UUID primary key (see https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#mapping-whole-column-declarations-to-python-types)
primary_key = Annotated[uuid.UUID, mapped_column(primary_key=True)]


class Base(DeclarativeBase):
    """Base class for all models.

    The type map is overriden to use our custom datetime type (see https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#customizing-the-type-map)"""

    type_annotation_map = {
        bool: types.Boolean(),
        datetime.date: types.Date(),
        datetime.datetime: TZDateTime(),
        str: types.String(),
        uuid.UUID: types.Uuid(),
    }
