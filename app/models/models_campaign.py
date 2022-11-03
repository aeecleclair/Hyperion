from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base


class ListMemberships(Base):
    __tablename__ = "campaign_lists_membership"

    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True)
    group_id: str = Column(ForeignKey("campaign_lists.id"), primary_key=True)
    role: str = Column(String)


class Sections(Base):
    __tablename__ = "campaign_sections"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, unique=True)
    description: str = Column(String)


class Lists(Base):
    __tablename__ = "campaign_lists"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, unique=True)
    description: str = Column(String)
    section: str = Column(ForeignKey("campaign_sections.id"))
    type: str = Column(String, nullable=False)
    members: list[ListMemberships] = relationship(
        "ListMemberships",
    )


class Votes(Base):
    __tablename__ = "campaign_votes"

    id = Column(String, primary_key=True)
    list_id: str = Column(ForeignKey("campaign_lists.id"), nullable=False)


class HasVoted(Base):
    __tablename__ = "campaign_has_voted"

    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True)
    section_id: str = Column(ForeignKey("campaign_sections.id"))
