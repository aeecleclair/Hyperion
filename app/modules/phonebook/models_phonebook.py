from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.phonebook.types_phonebook import Kinds
from app.types.sqlalchemy import Base


class Membership(Base):
    __tablename__ = "phonebook_membership"

    id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    association_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("phonebook_association.id"),
        primary_key=True,
    )
    mandate_year: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str] = mapped_column(String, nullable=False)
    role_tags: Mapped[str] = mapped_column(String, nullable=False)


class Association(Base):
    __tablename__ = "phonebook_association"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    kind: Mapped[Kinds] = mapped_column(Enum(Kinds), nullable=False)
    mandate_year: Mapped[int] = mapped_column(Integer, nullable=False)
