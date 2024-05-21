import uuid
from datetime import date

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.reception.types_reception import (
    AvailableMembership,
    DocumentSignatureType,
    PaymentType,
)
from app.types.sqlalchemy import Base, PrimaryKey


class Seller(Base):
    __tablename__ = "reception_seller"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    products: Mapped[list["ReceptionProduct"]] = relationship("ReceptionProduct")
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core_group.id"),
    )
    order: Mapped[int]


reception_document_constraint = Table(
    "reception_document_constraint",
    Base.metadata,
    Column("product_id", ForeignKey("reception_product.id"), primary_key=True),
    Column("document_id", ForeignKey("reception_document.id"), primary_key=True),
)


class ProductConstraint(Base):
    __tablename__ = "reception_product_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_product.id"),
        primary_key=True,
    )
    product_constraint_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_product.id"),
        primary_key=True,
    )


class ReceptionProduct(Base):
    __tablename__ = "reception_product"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_seller.id"),
    )
    name: Mapped[str]
    description: Mapped[str | None]
    public_display: Mapped[bool]
    product_constraints: Mapped[list["ReceptionProduct"]] = relationship(
        "ReceptionProduct",
        secondary="reception_product_constraint",
        primaryjoin="ReceptionProduct.id==ProductConstraint.product_id",
        secondaryjoin="ReceptionProduct.id==ProductConstraint.product_constraint_id",
    )
    document_constraints: Mapped[list["Document"]] = relationship(
        "Document",
        secondary="reception_document_constraint",
    )


class Curriculum(Base):
    __tablename__ = "reception_curriculum"

    id: Mapped[PrimaryKey]
    name: Mapped[str]


class CurriculumMembership(Base):
    __tablename__ = "reception_curriculum_membership"

    user_id = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    curriculum_id = mapped_column(
        UUID,
        ForeignKey("reception_curriculum.id"),
        primary_key=True,
    )


reception_allowed_curriculum = Table(
    "reception_allowed_curriculum",
    Base.metadata,
    Column(
        "product_variant_id",
        ForeignKey("reception_product_variant.id"),
        primary_key=True,
    ),
    Column("curriculum_id", ForeignKey("reception_curriculum.id"), primary_key=True),
)


class ProductVariant(Base):
    __tablename__ = "reception_product_variant"

    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reception_product.id"),
    )
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[int]
    enabled: Mapped[bool]
    unique: Mapped[bool]
    allowed_curriculum: Mapped[Curriculum] = relationship(
        "Curriculum",
        secondary="reception_allowed_curriculum",
    )


class Document(Base):
    __tablename__ = "reception_document"

    id: Mapped[PrimaryKey]
    name: Mapped[str]


class Purchase(Base):
    __tablename__ = "reception_purchase"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_product_variant.id"),
        primary_key=True,
    )
    quantity: Mapped[int]
    paid: Mapped[bool]


class Signature(Base):
    __tablename__ = "reception_signature"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_document.id"),
        primary_key=True,
    )
    signature_type: Mapped[DocumentSignatureType] = mapped_column(
        index=True,
    )
    numeric_signature_id: Mapped[str | None]


class Payment(Base):
    __tablename__ = "reception_payment"

    id: Mapped[PrimaryKey]
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
    )
    total: Mapped[int]
    payment_type: Mapped[PaymentType] = mapped_column(
        index=True,
    )


class Membership(Base):
    __tablename__ = "reception_membership"

    id: Mapped[PrimaryKey]
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
    )
    membership: Mapped[AvailableMembership] = mapped_column(
        index=True,
    )
    start_date: Mapped[date]
    end_date: Mapped[date]


class Status(Base):
    __tablename__ = "reception_status"

    id: Mapped[str] = mapped_column(primary_key=True)
    editable: Mapped[bool]
