import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.core.ticket.models_ticket import TicketGenerator

from app.modules.purchases.types_purchases import (
    DocumentSignatureType,
    PaymentType,
    PurchasesLogActionType,
)
from app.types.membership import AvailableAssociationMembership
from app.types.sqlalchemy import Base, PrimaryKey


class Seller(Base):
    __tablename__ = "purchases_seller"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
        nullable=False,
    )
    order: Mapped[int]


class DocumentConstraint(Base):
    __tablename__ = "purchases_document_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_document.id"),
        primary_key=True,
    )


class ProductConstraint(Base):
    __tablename__ = "purchases_product_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product.id"),
        primary_key=True,
    )
    product_constraint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product.id"),
        primary_key=True,
    )


class PurchasesTicketGenerator(Base):
    __tablename__ = "purchases_ticket_generator"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product.id"),
        primary_key=True,
    )
    generator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_generator.id"),
        primary_key=True,
    )


class PurchasesProduct(Base):
    __tablename__ = "purchases_product"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_seller.id"),
    )
    name_fr: Mapped[str]
    name_en: Mapped[str | None]
    description_fr: Mapped[str | None]
    description_en: Mapped[str | None]
    available_online: Mapped[bool]
    product_constraints: Mapped[list["PurchasesProduct"]] = relationship(
        "PurchasesProduct",
        secondary="purchases_product_constraint",
        primaryjoin="ProductConstraint.product_id==PurchasesProduct.id",
        secondaryjoin="ProductConstraint.product_constraint_id==PurchasesProduct.id",
        lazy="joined",
        join_depth=1,
    )
    document_constraints: Mapped[list["Document"]] = relationship(
        "app.modules.purchases.models_purchases.Document",
        secondary="purchases_document_constraint",
        lazy="selectin",  # Constraints are always loaded in cruds so we set this to not have to put selectinload
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        lazy="selectin",
    )
    related_membership: Mapped[AvailableAssociationMembership | None]
    tickets: Mapped[list["TicketGenerator"]] = relationship(
        "TicketGenerator",
        secondary="purchases_ticket_generator",
        lazy="selectin",
    )


class Curriculum(Base):
    __tablename__ = "purchases_curriculum"

    id: Mapped[PrimaryKey]
    name: Mapped[str]


class CurriculumMembership(Base):
    __tablename__ = "purchases_curriculum_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_curriculum.id"),
        primary_key=True,
    )


class AllowedCurriculum(Base):
    __tablename__ = "purchases_allowed_curriculum"

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product_variant.id"),
        primary_key=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_curriculum.id"),
        primary_key=True,
    )


class ProductVariant(Base):
    __tablename__ = "purchases_product_variant"

    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product.id"),
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
        secondary="purchases_allowed_curriculum",
        lazy="selectin",
    )
    related_membership_added_duration: Mapped[timedelta | None]
    needs_validation: Mapped[bool]


class Document(Base):
    __tablename__ = "purchases_document"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_seller.id"),
    )
    name: Mapped[str]


class Purchase(Base):
    __tablename__ = "purchases_purchase"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product_variant.id"),
        primary_key=True,
    )
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    quantity: Mapped[int]
    paid: Mapped[bool]
    validated: Mapped[bool]
    purchased_on: Mapped[datetime]


class Signature(Base):
    __tablename__ = "purchases_signature"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_document.id"),
        primary_key=True,
    )
    signature_type: Mapped[DocumentSignatureType] = mapped_column(
        index=True,
    )
    numeric_signature_id: Mapped[str | None]


class Payment(Base):
    __tablename__ = "purchases_payment"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    total: Mapped[int]
    payment_type: Mapped[PaymentType] = mapped_column(
        index=True,
    )


class PurchasesAction(Base):
    __tablename__ = "purchases_action"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=True,
    )  # Who made the request
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )  # For who the request was made
    action_type: Mapped[PurchasesLogActionType]
    action: Mapped[str]
    timestamp: Mapped[datetime]


class Checkout(Base):
    __tablename__ = "purchases_checkout"
    id: Mapped[PrimaryKey]
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    checkout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_checkout.id"))
    paid_products_ids: Mapped[list[ProductVariant]] = relationship(
        "ProductVariant",
        secondary="purchases_checkout_paid_product",
        lazy="selectin",
    )


class CheckoutPaidProduct(Base):
    __tablename__ = "purchases_checkout_paid_product"
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
        primary_key=True,
    )
    product_variant_id = mapped_column(
        ForeignKey("purchases_product_variant.id"),
        nullable=False,
        primary_key=True,
    )
    checkout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchases_checkout.id"))


class CustomDataField(Base):
    __tablename__ = "purchases_customdata_field"
    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_product.id"),
    )
    name: Mapped[str]
    user_can_answer: Mapped[bool]


class CustomData(Base):
    __tablename__ = "purchases_customdata"
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_customdata_field.id"),
        primary_key=True,
    )
    field: Mapped["CustomDataField"] = relationship("CustomDataField")
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    value: Mapped[str]


class CustomDataOption(Base):
    __tablename__ = "purchases_customdata_option"
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases_customdata_field.id"),
        primary_key=True,
    )
    option: Mapped[str]
