import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.core.models_core import CoreUser
from app.modules.cdr.types_cdr import (
    CdrLogActionType,
    DocumentSignatureType,
    PaymentType,
)
from app.types.membership import AvailableAssociationMembership
from app.types.sqlalchemy import Base, PrimaryKey


class Seller(Base):
    __tablename__ = "cdr_seller"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
        nullable=False,
    )
    order: Mapped[int]


class DocumentConstraint(Base):
    __tablename__ = "cdr_document_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_document.id"),
        primary_key=True,
    )


class ProductConstraint(Base):
    __tablename__ = "cdr_product_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
        primary_key=True,
    )
    product_constraint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
        primary_key=True,
    )


class CdrProduct(Base):
    __tablename__ = "cdr_product"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_seller.id"),
    )
    name_fr: Mapped[str]
    name_en: Mapped[str | None]
    description_fr: Mapped[str | None]
    description_en: Mapped[str | None]
    available_online: Mapped[bool]
    product_constraints: Mapped[list["CdrProduct"]] = relationship(
        "CdrProduct",
        secondary="cdr_product_constraint",
        primaryjoin="ProductConstraint.product_id==CdrProduct.id",
        secondaryjoin="ProductConstraint.product_constraint_id==CdrProduct.id",
        lazy="joined",
        join_depth=1,
    )
    document_constraints: Mapped[list["Document"]] = relationship(
        "Document",
        secondary="cdr_document_constraint",
        lazy="selectin",  # Constraints are always loaded in cruds so we set this to not have to put selectinload
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        lazy="selectin",
    )
    related_membership: Mapped[AvailableAssociationMembership | None]
    generate_ticket: Mapped[bool]
    ticket_max_use: Mapped[int | None]
    ticket_expiration: Mapped[datetime | None]


class Curriculum(Base):
    __tablename__ = "cdr_curriculum"

    id: Mapped[PrimaryKey]
    name: Mapped[str]


class CurriculumMembership(Base):
    __tablename__ = "cdr_curriculum_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_curriculum.id"),
        primary_key=True,
    )


class AllowedCurriculum(Base):
    __tablename__ = "cdr_allowed_curriculum"

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
        primary_key=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_curriculum.id"),
        primary_key=True,
    )


class ProductVariant(Base):
    __tablename__ = "cdr_product_variant"

    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
    )
    name_fr: Mapped[str]
    name_en: Mapped[str | None]
    description_fr: Mapped[str | None]
    description_en: Mapped[str | None]
    price: Mapped[int]
    enabled: Mapped[bool]
    unique: Mapped[bool]
    allowed_curriculum: Mapped[list[Curriculum]] = relationship(
        "Curriculum",
        secondary="cdr_allowed_curriculum",
        lazy="selectin",
    )
    related_membership_added_duration: Mapped[timedelta | None]


class Document(Base):
    __tablename__ = "cdr_document"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_seller.id"),
    )
    name: Mapped[str]


class Purchase(Base):
    __tablename__ = "cdr_purchase"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
        primary_key=True,
    )
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    quantity: Mapped[int]
    validated: Mapped[bool]
    purchased_on: Mapped[datetime]


class Signature(Base):
    __tablename__ = "cdr_signature"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_document.id"),
        primary_key=True,
    )
    signature_type: Mapped[DocumentSignatureType] = mapped_column(
        index=True,
    )
    numeric_signature_id: Mapped[str | None]


class Payment(Base):
    __tablename__ = "cdr_payment"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    total: Mapped[int]
    payment_type: Mapped[PaymentType] = mapped_column(
        index=True,
    )


class CdrAction(Base):
    __tablename__ = "cdr_action"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=True,
    )  # Who made the request
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )  # For who the request was made
    action_type: Mapped[CdrLogActionType]
    action: Mapped[str]
    timestamp: Mapped[datetime]


class Checkout(Base):
    __tablename__ = "cdr_checkout"
    id: Mapped[PrimaryKey]
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    checkout_id = mapped_column(ForeignKey("payment_checkout.id"))


class Ticket(Base):
    __tablename__ = "cdr_ticket"
    id: Mapped[PrimaryKey]
    secret: Mapped[uuid.UUID]
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
    )
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    user: Mapped["CoreUser"] = relationship("CoreUser")
    scan_left: Mapped[int]
    tags: Mapped[str]
    expiration: Mapped[datetime]


class CustomDataField(Base):
    __tablename__ = "cdr_customdata_field"
    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_seller.id"),
    )
    name: Mapped[str]


class CustomData(Base):
    __tablename__ = "cdr_customdata"
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_customdata_field.id"),
        primary_key=True,
    )
    field = relationship("CustomDataField")
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    value: Mapped[str]
