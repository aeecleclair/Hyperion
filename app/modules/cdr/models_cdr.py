import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.cdr.types_cdr import (
    AvailableMembership,
    CdrLogActionType,
    DocumentSignatureType,
    PaymentType,
)
from app.types.sqlalchemy import Base, PrimaryKey, TZDateTime


class Seller(Base):
    __tablename__ = "cdr_seller"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    group_id = mapped_column(
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
    name_en: Mapped[str]
    description_fr: Mapped[str | None] = mapped_column(String, nullable=True)
    description_en: Mapped[str | None] = mapped_column(String, nullable=True)
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
        lazy="selectin",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        lazy="selectin",
    )
    related_membership: Mapped[AvailableMembership | None] = mapped_column(
        nullable=True,
    )


class Curriculum(Base):
    __tablename__ = "cdr_curriculum"

    id: Mapped[PrimaryKey]
    name: Mapped[str]


class CurriculumMembership(Base):
    __tablename__ = "cdr_curriculum_membership"

    user_id = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    curriculum_id = mapped_column(
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
    name_en: Mapped[str]
    description_fr: Mapped[str | None] = mapped_column(String, nullable=True)
    description_en: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[int]
    enabled: Mapped[bool]
    unique: Mapped[bool]
    allowed_curriculum: Mapped[list[Curriculum]] = relationship(
        "Curriculum",
        secondary="cdr_allowed_curriculum",
        lazy="selectin",
    )


class Document(Base):
    __tablename__ = "cdr_document"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_seller.id"),
    )
    name: Mapped[str]


class Purchase(Base):
    __tablename__ = "cdr_purchase"

    user_id = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
        primary_key=True,
    )
    quantity: Mapped[int]
    validated: Mapped[bool]


class Signature(Base):
    __tablename__ = "cdr_signature"

    user_id = mapped_column(
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
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    total: Mapped[int]
    payment_type: Mapped[PaymentType] = mapped_column(
        index=True,
    )


class Membership(Base):
    __tablename__ = "cdr_membership"

    id: Mapped[PrimaryKey]
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    membership: Mapped[AvailableMembership] = mapped_column(
        index=True,
    )
    start_date: Mapped[date]
    end_date: Mapped[date]


class CdrAction(Base):
    __tablename__ = "cdr_action"

    id: Mapped[PrimaryKey]
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=True,
    )  # Who made the request
    subject_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )  # For who the request was made
    action_type: Mapped[CdrLogActionType]
    action: Mapped[str]
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)