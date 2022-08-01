from datetime import date, datetime

from sqlalchemy import TEXT, Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreGroup, CoreUser


class LoanContent(Base):
    __tablename__ = "loan_content"

    loan_id: str = Column(ForeignKey("loan.id"), primary_key=True)
    item_id: str = Column(ForeignKey("item.id"), primary_key=True)


class Item(Base):
    __tablename__ = "item"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String)
    caution: str = Column(String)
    group_id: str = Column(ForeignKey("core_group.id"), index=True)
    group: CoreGroup = relationship(
        "CoreGroup",
    )
    expiration: date = Column(Date, nullable=False)

    loan: list["Loan"] = relationship("Loan", secondary="loan_content")


class Loan(Base):
    __tablename__ = "loan"

    id: str = Column(String, primary_key=True, index=True)
    # link the table Loan to the table CoreUser with a one to many relationship on the id_user

    borrower_id: str = Column(
        ForeignKey("core_user.id"),
        index=True,
    )
    borrower: CoreUser = relationship(
        "CoreUser",
    )
    start: datetime | None = Column(DateTime, nullable=False)
    end: datetime | None = Column(DateTime, nullable=False)
    notes: str | None = Column(TEXT, nullable=False)
    returned: bool = Column(Boolean)
    caution: bool = Column(Boolean, nullable=False)

    item: list["Item"] = relationship(
        "Item",
        secondary="loan_content",
    )
