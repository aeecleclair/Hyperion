from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class Pixel(Base):
    __tablename__ = "pixels"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    date: Mapped[datetime]
    x: Mapped[int]
    y: Mapped[int]
    color: Mapped[str]
