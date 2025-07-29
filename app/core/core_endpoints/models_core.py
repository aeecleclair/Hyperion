"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.groups.groups_type import AccountType
from app.types.sqlalchemy import Base, PrimaryKey


class CoreData(Base):
    """
    A table to store arbitrary data.

     - schema: the name of the schema allowing to deserialize the data.
     - data: the json data.

    Use `get_core_data` and `set_core_data` utils to interact with this table.
    """

    __tablename__ = "core_data"

    schema: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[str]


class EmailQueue(Base):
    """
    A table to store emails to be sent. This allows to send low priority emails, without risking to be ratelimited by the email provider.
    Emails are sent by a queued task every hour.
    """

    __tablename__ = "email_queue"

    id: Mapped[PrimaryKey]
    email: Mapped[str]
    subject: Mapped[str]
    body: Mapped[str]
    created_on: Mapped[datetime]


class ModuleGroupVisibility(Base):
    __tablename__ = "module_group_visibility"

    root: Mapped[str] = mapped_column(primary_key=True)
    allowed_group_id: Mapped[str] = mapped_column(primary_key=True)


class ModuleAccountTypeVisibility(Base):
    __tablename__ = "module_account_type_visibility"

    root: Mapped[str] = mapped_column(primary_key=True)
    allowed_account_type: Mapped[AccountType] = mapped_column(primary_key=True)


class AlembicVersion(Base):
    """
    A table managed exclusively by Alembic, used to keep track of the database schema version.
    This model allows to have exactly the same tables in the models and in the database.
    Without this model, SQLAlchemy `conn.run_sync(Base.metadata.drop_all)` will ignore this table.

    WARNING: Hyperion should not modify this table.
    """

    __tablename__ = "alembic_version"

    version_num: Mapped[str] = mapped_column(primary_key=True)
