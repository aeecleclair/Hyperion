from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.groups.groups_type import AccountType
from app.types.sqlalchemy import Base


class CorePermissionGroup(Base):
    __tablename__ = "core_permission_group"

    permission_name: Mapped[str] = mapped_column(primary_key=True, index=True)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
        index=True,
        primary_key=True,
    )


class CorePermissionAccountType(Base):
    __tablename__ = "core_permission_account_type"

    permission_name: Mapped[str] = mapped_column(primary_key=True, index=True)
    account_type: Mapped[AccountType] = mapped_column(
        index=True,
        primary_key=True,
    )
