from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import models_core
from app.modules.campaign.types_campaign import StatusType
from app.types.sqlalchemy import Base


class ListMemberships(Base):
    __tablename__ = "campaign_lists_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    list_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_lists.id"),
        primary_key=True,
    )
    user: Mapped[models_core.CoreUser] = relationship("CoreUser")
    lists: Mapped["Lists"] = relationship("Lists", back_populates="members")
    role: Mapped[str] = mapped_column(String)


class Sections(Base):
    __tablename__ = "campaign_sections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(String)
    lists: Mapped[list["Lists"]] = relationship("Lists", back_populates="section")


class Lists(Base):
    __tablename__ = "campaign_lists"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    section_id: Mapped[str] = mapped_column(ForeignKey("campaign_sections.id"))
    section: Mapped[Sections] = relationship("Sections", back_populates="lists")
    type: Mapped[str] = mapped_column(String, nullable=False)
    members: Mapped[list[ListMemberships]] = relationship(
        "ListMemberships",
        back_populates="lists",
    )
    program: Mapped[str | None] = mapped_column(String)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class VoterGroups(Base):
    """
    VoterGroups are groups allowed to vote for a campaign
    """

    __tablename__ = "campaign_voter_groups"

    group_id: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)


class Votes(Base):
    __tablename__ = "campaign_votes"

    id = mapped_column(String, primary_key=True)
    list_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_lists.id"),
        nullable=False,
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

    id: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    status: Mapped[StatusType] = mapped_column(Enum(StatusType), nullable=False)
