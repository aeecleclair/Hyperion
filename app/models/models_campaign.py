from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models import models_core


class ListMemberships(Base):
    __tablename__ = "campaign_lists_membership"

    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True)
    list_id: str = Column(ForeignKey("campaign_lists.id"), primary_key=True)
    user: models_core.CoreUser = relationship("CoreUser")
    lists: "Lists" = relationship("Lists", back_populates="members")
    role: str = Column(String)


class Sections(Base):
    __tablename__ = "campaign_sections"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, unique=True)
    description: str = Column(String)
    lists: list["Lists"] = relationship("Lists", back_populates="section")


class Lists(Base):
    __tablename__ = "campaign_lists"

    id: str = Column(String, primary_key=True)
    name: str = Column(String)
    description: str = Column(String)
    section_id: str = Column(ForeignKey("campaign_sections.id"))
    section: Sections = relationship("Sections", back_populates="lists")
    type: str = Column(String, nullable=False)
    members: list[ListMemberships] = relationship(
        "ListMemberships", back_populates="lists"
    )
    program: str | None = Column(String)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Votes(Base):
    __tablename__ = "campaign_votes"

    id = Column(String, primary_key=True)
    list_id: str = Column(ForeignKey("campaign_lists.id"), nullable=False)


class HasVoted(Base):
    __tablename__ = "campaign_has_voted"

    # There are two primary keys, has each user_id and section_id will be used multiple times but the combinaison of the two should always be unique
    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True)
    section_id: str = Column(ForeignKey("campaign_sections.id"), primary_key=True)


class Status(Base):
    __tablename__ = "campaign_status"

    id: str = Column(String, nullable=False, primary_key=True)
    status: str = Column(String, nullable=False)
