from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base, PrimaryKey
from app.core.core_endpoints.models_core import CoreUser


class Pixel(Base):
    __tablename__ = "pixels"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    color: Mapped[str]
    date: Mapped[datetime]
    x: Mapped[int]
    y: Mapped[int]
