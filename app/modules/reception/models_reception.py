import uuid
from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.reception.types_reception import (
    AvailableMembership,
    DocumentSignatureType,
    PaymentType,
)
from app.types.sqlalchemy import Base


class Seller(Base):
    __tablename__ = "reception_seller"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    products: Mapped[list["ReceptionProduct"]] = relationship("ReceptionProduct")
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_group.id"),
    )
    order: Mapped[int] = mapped_column(Integer)


document_constraints_association_table = Table(
    "document_constraints_association_table",
    Base.metadata,
    Column("product_id", ForeignKey("reception_product.id"), primary_key=True),
    Column("document_id", ForeignKey("reception_document.id"), primary_key=True),
)


class ProductConstraints(Base):
    __tablename__ = "product_constraints_association_table"

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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_seller.id"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    public_display: Mapped[bool] = mapped_column(Boolean, nullable=False)
    product_constraints: Mapped[list["ReceptionProduct"]] = relationship(
        "ReceptionProduct",
        secondary="product_constraints_association_table",
        primaryjoin="ReceptionProduct.id==ProductConstraints.product_id",
        secondaryjoin="ReceptionProduct.id==ProductConstraints.product_constraint_id",
    )
    document_constraints: Mapped[list["Document"]] = relationship(
        "Document",
        secondary="document_constraints_association_table",
    )


class Curriculum(Base):
    __tablename__ = "reception_curriculum"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)


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


allowed_curriculum_association_table = Table(
    "allowed_curriculum_association_table",
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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("reception_product.id"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unique: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allowed_curriculum: Mapped[Curriculum] = relationship(
        "Curriculum",
        secondary="allowed_curriculum_association_table",
    )


class Document(Base):
    __tablename__ = "reception_document"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)


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
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False)


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
        String,
        nullable=False,
        index=True,
    )
    numeric_signature_id: Mapped[str] = mapped_column(String, nullable=True)


class Payment(Base):
    __tablename__ = "reception_payment"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
    )
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[PaymentType] = mapped_column(
        String,
        nullable=False,
        index=True,
    )


class Membership(Base):
    __tablename__ = "reception_membership"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        index=True,
        nullable=False,
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("core_user.id"),
    )
    membership: Mapped[AvailableMembership] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class Status(Base):
    __tablename__ = "reception_status"

    id: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    editable: Mapped[bool] = mapped_column(Boolean, nullable=False)
