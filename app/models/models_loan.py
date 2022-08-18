from datetime import date, timedelta

from sqlalchemy import (
    TEXT,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Interval,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models import models_core


class Loaner(Base):
    __tablename__ = "loaner"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)
    group_manager_id: str = Column(String, nullable=False)

    items: list["Item"] = relationship("Item")
    loans: list["Loan"] = relationship("Loan")


class LoanContent(Base):
    __tablename__ = "loan_content"

    loan_id: str = Column(ForeignKey("loan.id"), primary_key=True)
    item_id: str = Column(ForeignKey("loaner_item.id"), primary_key=True)


class Item(Base):
    __tablename__ = "loaner_item"

    id: str = Column(String, primary_key=True, index=True)
    # Two items with the same name may exist in two different loaners
    name: str = Column(String, nullable=False)
    loaner_id: str = Column(String, ForeignKey("loaner.id"))
    suggested_caution: int = Column(Integer)
    multiple: bool = Column(Boolean)

    suggested_lending_duration: timedelta = Column(Interval, nullable=False)

    available: bool | None = Column(Boolean)

    # The loaner field won't usually be returned. We won't to only fetch it from the database when it is accessed
    loaner: Loaner = relationship(Loaner, lazy="select")


class Loan(Base):
    __tablename__ = "loan"

    id: str = Column(String, primary_key=True, index=True)
    # link the table Loan to the table CoreUser with a one to many relationship on the id_user

    borrower_id: str = Column(
        ForeignKey("core_user.id"),
        index=True,
    )
    borrower: models_core.CoreUser = relationship("CoreUser", lazy="select")
    loaner_id: str = Column(
        String,
        ForeignKey("loaner.id"),
        index=True,
    )
    # The loaner field won't usually be returned. We won't to only fetch it from the database when it is accessed
    loaner: Loaner = relationship("Loaner", lazy="select")
    start: date = Column(Date, nullable=False)
    end: date = Column(Date, nullable=False)
    notes: str | None = Column(TEXT)
    caution: str | None = Column(String)
    returned: bool = Column(Boolean, nullable=False)

    items: list["Item"] = relationship(
        "Item",
        secondary="loan_content",
    )
