from sqlalchemy import Column, ForeignKey, String

from app.database import Base


class Sections(Base):
    __tablename__ = "campaign_sections"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, unique=True)
    description: str = Column(String)
    logo_path: str = Column(String, nullable=False)


class Lists(Base):
    __tablename__ = "campaign_lists"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, unique=True)
    description: str = Column(String)
    section_id: str = Column(ForeignKey("campaign_sections.id"))
    type: str = Column(String, nullable=False)
    logo_path: str = Column(String, nullable=False)
    picture_path: str = Column(String)


class ListMemberships(Base):
    __tablename__ = "campaign_lists_membership"

    id = Column(String, primary_key=True)
    user_id: str = Column(ForeignKey("core_user.id"), nullable=False)
    group_id: str = Column(ForeignKey("campaign_lists.id"), nullable=False)
    role: str = Column(String)


class Votes(Base):
    __tablename__ = "campaign_votes"

    id = Column(String, primary_key=True)
    list_id: str = Column(ForeignKey("campaign_lists.id"), nullable=False)


class HasVoted(Base):
    __tablename__ = "campagin_has_voted"

    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True)
