from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import models_core
from app.utils.types.tricount_types import TransactionType


class SharerGroup(Base):
    __tablename__ = "tricount_sharer_group"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship()
    members: Mapped[list[models_core.CoreUser]] = relationship(
        secondary="tricount_sharer_group_membership"
    )


class SharerGroupMembership(Base):
    __tablename__ = "tricount_sharer_group_membership"

    sharer_group_id: Mapped[str] = mapped_column(
        ForeignKey("tricount_sharer_group.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    # We let the user choose in what order they want to see the sharer groups using `rank`
    # A SharerGroupMembership with a rank of 0 will be displayed first, then 1, then 2
    position: Mapped[int] = mapped_column(Float, nullable=False)
    # A membership may be inactive if the user was removed from the sharergroup
    # An inactive user should not be allowed to edit the sharergroup
    # and its balance should only be returned if its not 0.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Transaction(Base):
    __tablename__ = "tricount_transaction"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    sharer_group_id: Mapped[str] = mapped_column(
        ForeignKey("tricount_sharer_group.id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    creation_datetime: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    update_datetime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    creator_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)
    payer_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)

    # beneficiary_id: Mapped[str | None] = mapped_column(ForeignKey("core_user.id"))
    beneficiaries: Mapped[list[models_core.CoreUser]] = relationship(
        secondary="tricount_transaction_beneficiaries_membership",
    )


class TransactionBeneficiariesMembership(Base):
    __tablename__ = "tricount_transaction_beneficiaries_membership"

    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("tricount_transaction.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
