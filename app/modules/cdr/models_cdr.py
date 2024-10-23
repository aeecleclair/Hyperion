import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

if TYPE_CHECKING:
    from app.core.models_core import CoreUser
from app.modules.cdr.types_cdr import (
    CdrLogActionType,
    DocumentSignatureType,
    PaymentType,
)
from app.types.membership import AvailableAssociationMembership
from app.types.sqlalchemy import Base, PrimaryKey


class Seller(MappedAsDataclass, Base):
    __tablename__ = "cdr_seller"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
    )
    order: Mapped[int]


class DocumentConstraint(MappedAsDataclass, Base):
    __tablename__ = "cdr_document_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_document.id"),
        primary_key=True,
    )


class ProductConstraint(MappedAsDataclass, Base):
    __tablename__ = "cdr_product_constraint"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
        primary_key=True,
    )
    product_constraint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
        primary_key=True,
    )


class TicketGenerator(MappedAsDataclass, Base):
    __tablename__ = "cdr_ticket_generator"

    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
    )
    name: Mapped[str]
    max_use: Mapped[int]
    expiration: Mapped[datetime]


class CdrProduct(MappedAsDataclass, Base):
    __tablename__ = "cdr_product"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_seller.id"),
    )
    name_fr: Mapped[str]
    name_en: Mapped[str | None]
    available_online: Mapped[bool]

    description_fr: Mapped[str | None] = mapped_column(default=None)
    description_en: Mapped[str | None] = mapped_column(default=None)

    product_constraints: Mapped[list["CdrProduct"]] = relationship(
        "CdrProduct",
        secondary="cdr_product_constraint",
        primaryjoin="ProductConstraint.product_id==CdrProduct.id",
        secondaryjoin="ProductConstraint.product_constraint_id==CdrProduct.id",
        lazy="joined",
        join_depth=1,
        init=False,
    )
    document_constraints: Mapped[list["Document"]] = relationship(
        "app.modules.cdr.models_cdr.Document",
        secondary="cdr_document_constraint",
        lazy="selectin",  # Constraints are always loaded in cruds so we set this to not have to put selectinload
        init=False,
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        lazy="selectin",
        init=False,
    )
    tickets: Mapped[list["TicketGenerator"]] = relationship(
        "TicketGenerator",
        lazy="selectin",
        init=False,
    )

    related_membership: Mapped[AvailableAssociationMembership | None] = mapped_column(
        default=None,
    )


class Curriculum(MappedAsDataclass, Base):
    __tablename__ = "cdr_curriculum"

    id: Mapped[PrimaryKey]
    name: Mapped[str]


class CurriculumMembership(MappedAsDataclass, Base):
    __tablename__ = "cdr_curriculum_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_curriculum.id"),
        primary_key=True,
    )


class AllowedCurriculum(MappedAsDataclass, Base):
    __tablename__ = "cdr_allowed_curriculum"

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
        primary_key=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_curriculum.id"),
        primary_key=True,
    )


class ProductVariant(MappedAsDataclass, Base):
    __tablename__ = "cdr_product_variant"

    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
    )
    name_fr: Mapped[str]
    name_en: Mapped[str | None]
    price: Mapped[int]
    enabled: Mapped[bool]
    unique: Mapped[bool]
    related_membership_added_duration: Mapped[timedelta | None] = mapped_column(
        default=None,
    )

    description_fr: Mapped[str | None] = mapped_column(default=None)
    description_en: Mapped[str | None] = mapped_column(default=None)

    allowed_curriculum: Mapped[list[Curriculum]] = relationship(
        "Curriculum",
        secondary="cdr_allowed_curriculum",
        lazy="selectin",
        init=False,
    )


class Document(MappedAsDataclass, Base):
    __tablename__ = "cdr_document"

    id: Mapped[PrimaryKey]
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_seller.id"),
    )
    name: Mapped[str]


class Purchase(MappedAsDataclass, Base):
    __tablename__ = "cdr_purchase"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
        primary_key=True,
    )

    quantity: Mapped[int]
    validated: Mapped[bool]
    purchased_on: Mapped[datetime]

    product_variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant",
        init=False,
    )


class Signature(MappedAsDataclass, Base):
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


class Payment(MappedAsDataclass, Base):
    __tablename__ = "cdr_payment"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    total: Mapped[int]
    payment_type: Mapped[PaymentType] = mapped_column(
        index=True,
    )


class CdrAction(MappedAsDataclass, Base):
    __tablename__ = "cdr_action"

    id: Mapped[PrimaryKey]
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )  # For who the request was made
    action_type: Mapped[CdrLogActionType]
    action: Mapped[str]
    timestamp: Mapped[datetime]
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_user.id"),
        default=None,
    )  # Who made the request


class Checkout(MappedAsDataclass, Base):
    __tablename__ = "cdr_checkout"
    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    checkout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_checkout.id"))


class Ticket(MappedAsDataclass, Base):
    __tablename__ = "cdr_ticket"
    id: Mapped[PrimaryKey]
    secret: Mapped[uuid.UUID] = mapped_column(unique=True)
    generator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_ticket_generator.id"),
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product_variant.id"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    name: Mapped[str]

    scan_left: Mapped[int]
    tags: Mapped[str]  # Comma separated values
    expiration: Mapped[datetime]
    user: Mapped["CoreUser"] = relationship(
        "CoreUser",
        init=False,
    )
    product_variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant",
        init=False,
    )


class CustomDataField(MappedAsDataclass, Base):
    __tablename__ = "cdr_customdata_field"
    id: Mapped[PrimaryKey]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_product.id"),
    )
    name: Mapped[str]


class CustomData(MappedAsDataclass, Base):
    __tablename__ = "cdr_customdata"
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cdr_customdata_field.id"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    value: Mapped[str]
    field: Mapped["CustomDataField"] = relationship("CustomDataField", init=False)
