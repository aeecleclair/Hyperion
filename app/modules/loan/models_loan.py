from datetime import date

from sqlalchemy import TEXT, Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import models_core
from app.types.sqlalchemy import Base


class Loaner(Base):
    __tablename__ = "loaner"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    group_manager_id: Mapped[str] = mapped_column(String, nullable=False)

    items: Mapped[list["Item"]] = relationship(
        "Item",
        lazy="joined",
        back_populates="loaner",
    )
    loans: Mapped[list["Loan"]] = relationship(
        "Loan",
        lazy="joined",
        back_populates="loaner",
    )


class LoanContent(Base):
    __tablename__ = "loan_content"

    loan_id: Mapped[str] = mapped_column(ForeignKey("loan.id"), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("loaner_item.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    loan: Mapped["Loan"] = relationship("Loan")
    item: Mapped["Item"] = relationship("Item")


class Item(Base):
    __tablename__ = "loaner_item"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    # Two items with the same name may exist in two different loaners
    name: Mapped[str] = mapped_column(String, nullable=False)
    loaner_id: Mapped[str] = mapped_column(String, ForeignKey("loaner.id"))
    suggested_caution: Mapped[int] = mapped_column(Integer)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_lending_duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )  # duration in seconds
    loaner: Mapped[Loaner] = relationship(Loaner, lazy="joined", back_populates="items")


class Loan(Base):
    __tablename__ = "loan"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    # link the table Loan to the table CoreUser with a one-to-many relationship on the id_user

    borrower_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        index=True,
    )
    borrower: Mapped[models_core.CoreUser] = relationship("CoreUser", lazy="joined")
    loaner_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("loaner.id"),
        index=True,
    )
    loaner: Mapped[Loaner] = relationship(
        "Loaner",
        lazy="joined",
        back_populates="loans",
    )
    start: Mapped[date] = mapped_column(Date, nullable=False)
    end: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(TEXT)
    caution: Mapped[str | None] = mapped_column(String)
    returned: Mapped[bool] = mapped_column(Boolean, nullable=False)
    returned_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    items: Mapped[list["Item"]] = relationship(
        "Item",
        viewonly=True,
        secondary="loan_content",
        lazy="joined",
    )
