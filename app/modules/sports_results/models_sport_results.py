from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Tuple
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Captain(Base):
    __tablename__ = "sport-team-captain"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    sport: Mapped["Sport"] = relationship("Sport", back_populates="captain")


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    capitains: Mapped[list[Captain]] = relationship(
        "Captain",
        back_populates="sport",
    )


class Result(Base):
    __tablename__ = "result"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sport_id: Mapped[str] = mapped_column(String)
    score: Mapped[tuple] = mapped_column(
        Tuple
    )  # This may don't work but i'll fix it later
    rank: Mapped[int] = mapped_column(Integer)
    match_date: Mapped[date] = mapped_column(Date)
