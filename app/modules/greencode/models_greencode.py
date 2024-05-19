from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class GreenCodeItem(Base):
    __tablename__ = "greencode_items"

    id: Mapped[PrimaryKey]
    qr_code_content: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    memberships: Mapped[list["GreenCodeMembership"]] = relationship(
        "GreenCodeMembership",
    )


class GreenCodeMembership(Base):
    __tablename__ = "greencode_memberships"

    item_id: Mapped[str] = mapped_column(
        ForeignKey("greencode_items.id"),
        primary_key=True,
        nullable=False,
    )
    item: Mapped[GreenCodeItem] = relationship(
        "GreenCodeItem",
        back_populates="memberships",
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
        nullable=False,
    )
    user: Mapped[CoreUser] = relationship("CoreUser")
