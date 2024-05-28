from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base


class CaptainMembership(Base):
    __tablename__ = "sport_team_captain_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    sport_id: Mapped[str] = mapped_column(String)


class Captain(Base):
    __tablename__ = "sport_team-_captains"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    sport: Mapped["Sport"] = relationship(
        "Sport",
        back_populates="captain",
    )


class Sport(Base):
    __tablename__ = "sport_sports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    captains: Mapped[list[Captain]] = relationship(
        "Captain",
        back_populates="sport",
    )


class Result(Base):
    __tablename__ = "sport_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sport_id: Mapped[str] = mapped_column(String)
    score1: Mapped[int] = mapped_column(Integer)
    score2: Mapped[int] = mapped_column(Integer)
    rank: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String)
    match_date: Mapped[date] = mapped_column(Date)
