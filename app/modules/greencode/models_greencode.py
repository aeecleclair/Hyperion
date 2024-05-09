from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.types.sqlalchemy import Base


class Item(Base):
    __tablename__ = "greencode_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    qr_code_content: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    users: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        back_populates="items",
    )


class Membership(Base):
    __tablename__ = "greencode_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    item_id: Mapped[str] = mapped_column(
        ForeignKey("greencode_items.id"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("coreuser.id"),
        primary_key=True,
    )
    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        back_populates="greencode_items",
    )
