from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base

class CaptainsSports(Base):
    __tablename__ = "captains_sports"

    capitain_id: Mapped[str] = mapped_column(ForeignKey("sport_team_captains.id"), primary_key=True)
    sport_id: Mapped[str] = mapped_column(ForeignKey("sport_sports.id"), primary_key=True)

class Captain(Base):
    __tablename__ = "sport_team_captains"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)
    sports: Mapped[list["Sport"]] = relationship(
        "Sport",
        secondary="captains_sports",
        back_populates="captains",
    )


class Sport(Base):
    __tablename__ = "sport_sports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    captains: Mapped[list["Captain"]] = relationship(
        "Captain",
        secondary="captains_sports",
        back_populates="sports",
    )

class Result(Base):
    __tablename__ = "sport_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sport_id: Mapped[str] = mapped_column(String, nullable=False)
    score1: Mapped[int] = mapped_column(Integer, nullable=False)
    score2: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    match_date: Mapped[date] = mapped_column(Date, nullable=False)