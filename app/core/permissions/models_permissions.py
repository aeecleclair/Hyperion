from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base


class CorePermission(Base):
    __tablename__ = "core_permission"

    permission_name: Mapped[str] = mapped_column(primary_key=True, index=True)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
        index=True,
        primary_key=True,
    )
