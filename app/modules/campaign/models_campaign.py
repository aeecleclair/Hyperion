from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users import models_users
from app.modules.campaign.types_campaign import StatusType
from app.types.sqlalchemy import Base


class ListMemberships(Base):
    __tablename__ = "campaign_lists_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    list_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_lists.id"),
        primary_key=True,
    )
    role: Mapped[str]

    user: Mapped[models_users.CoreUser] = relationship("CoreUser", init=False)
    lists: Mapped["Lists"] = relationship("Lists", back_populates="members", init=False)


class Sections(Base):
    __tablename__ = "campaign_sections"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    lists: Mapped[list["Lists"]] = relationship(
        "Lists",
        back_populates="section",
        default_factory=list,
    )


class Lists(Base):
    __tablename__ = "campaign_lists"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    section_id: Mapped[str] = mapped_column(ForeignKey("campaign_sections.id"))
    type: Mapped[str]
    program: Mapped[str | None]
    members: Mapped[list[ListMemberships]] = relationship(
        "ListMemberships",
        back_populates="lists",
    )

    section: Mapped[Sections] = relationship(
        "Sections",
        back_populates="lists",
        init=False,
    )

    def as_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Votes(Base):
    __tablename__ = "campaign_votes"

    id: Mapped[str] = mapped_column(primary_key=True)
    list_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_lists.id"),
    )


class HasVoted(Base):
    __tablename__ = "campaign_has_voted"

    # There are two primary keys, has each user_id and section_id will be used multiple times but the combinaison of the two should always be unique
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    section_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_sections.id"),
        primary_key=True,
    )


class Status(Base):
    __tablename__ = "campaign_status"

    id: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[StatusType]
