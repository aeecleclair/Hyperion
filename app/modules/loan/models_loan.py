from datetime import date

from sqlalchemy import TEXT, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.core_endpoints import models_core
from app.types.sqlalchemy import Base


class Loaner(Base):
    __tablename__ = "loaner"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True)
    group_manager_id: Mapped[str]

    items: Mapped[list["Item"]] = relationship(
        "Item",
        lazy="joined",
        back_populates="loaner",
        default_factory=list,
    )
    loans: Mapped[list["Loan"]] = relationship(
        "Loan",
        lazy="joined",
        back_populates="loaner",
        default_factory=list,
    )


class LoanContent(Base):
    __tablename__ = "loan_content"

    loan_id: Mapped[str] = mapped_column(ForeignKey("loan.id"), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("loaner_item.id"), primary_key=True)
    quantity: Mapped[int]
    loan: Mapped["Loan"] = relationship("Loan", init=False)
    item: Mapped["Item"] = relationship("Item", init=False)


class Item(Base):
    __tablename__ = "loaner_item"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    # Two items with the same name may exist in two different loaners
    name: Mapped[str]
    loaner_id: Mapped[str] = mapped_column(ForeignKey("loaner.id"))
    suggested_caution: Mapped[int]
    total_quantity: Mapped[int]
    suggested_lending_duration: Mapped[int]  # duration in seconds
    loaner: Mapped[Loaner] = relationship(
        Loaner,
        lazy="joined",
        back_populates="items",
        init=False,
    )


class Loan(Base):
    __tablename__ = "loan"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    # link the table Loan to the table CoreUser with a one-to-many relationship on the id_user

    borrower_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        index=True,
    )
    loaner_id: Mapped[str] = mapped_column(
        ForeignKey("loaner.id"),
        index=True,
    )

    start: Mapped[date]
    end: Mapped[date]
    notes: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    caution: Mapped[str | None]
    returned: Mapped[bool]

    items: Mapped[list["Item"]] = relationship(
        "Item",
        viewonly=True,
        secondary="loan_content",
        lazy="joined",
    )

    returned_date: Mapped[date | None] = mapped_column(default=None)

    borrower: Mapped[models_core.CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )
    loaner: Mapped[Loaner] = relationship(
        "Loaner",
        lazy="joined",
        back_populates="loans",
        init=False,
    )
