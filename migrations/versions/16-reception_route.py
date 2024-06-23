"""16-cdr-route

Create Date: 2024-05-21 15:56:00.444337
"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "5d05a19f14bc"
down_revision: str | None = "bb8fbaf26f5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class AvailableMembership(Enum):
    aeecl = "AEECL"
    useecl = "USEECL"


class PaymentType(Enum):
    cash = "cash"
    check = "check"
    helloasso = "HelloAsso"
    card = "card"
    archived = "archived"


class DocumentSignatureType(Enum):
    physical = "physical"
    material = "material"


class CdrLogActionType(Enum):
    purchase_add = "purchase_add"
    purchase_delete = "purchase_delete"
    payment_add = "payment_add"
    payment_delete = "payment_delete"


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "cdr_curriculum",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cdr_document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["cdr_seller.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cdr_curriculum_membership",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("curriculum_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["curriculum_id"], ["cdr_curriculum.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("user_id", "curriculum_id"),
    )
    op.create_table(
        "cdr_membership",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "membership",
            sa.Enum(AvailableMembership, name="availablemembership"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cdr_membership_membership"),
        "cdr_membership",
        ["membership"],
        unique=False,
    )
    op.create_table(
        "cdr_payment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column(
            "payment_type",
            sa.Enum(
                PaymentType,
                name="paymenttype",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cdr_payment_payment_type"),
        "cdr_payment",
        ["payment_type"],
        unique=False,
    )
    # FIXME: The following table is missing the products column
    op.create_table(
        "cdr_seller",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["core_group.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cdr_signature",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column(
            "signature_type",
            sa.Enum(DocumentSignatureType, name="documentsignaturetype"),
            nullable=False,
        ),
        sa.Column("numeric_signature_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["cdr_document.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("user_id", "document_id"),
    )
    op.create_index(
        op.f("ix_cdr_signature_signature_type"),
        "cdr_signature",
        ["signature_type"],
        unique=False,
    )
    op.create_table(
        "cdr_product",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("name_fr", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("description_fr", sa.String(), nullable=True),
        sa.Column("description_en", sa.String(), nullable=True),
        sa.Column("available_online", sa.Boolean(), nullable=False),
        sa.Column(
            "related_membership",
            sa.Enum(
                AvailableMembership,
                name="availablemembership",
                extend_existing=True,
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["seller_id"], ["cdr_seller.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cdr_document_constraint",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["cdr_document.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["cdr_product.id"]),
        sa.PrimaryKeyConstraint("product_id", "document_id"),
    )
    op.create_table(
        "cdr_product_constraint",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_constraint_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["product_constraint_id"], ["cdr_product.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["cdr_product.id"]),
        sa.PrimaryKeyConstraint("product_id", "product_constraint_id"),
    )
    op.create_table(
        "cdr_product_variant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("name_fr", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("description_fr", sa.String(), nullable=True),
        sa.Column("description_en", sa.String(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("unique", sa.Boolean(), nullable=False),
        sa.Column("related_membership_added_duration", sa.Interval(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["cdr_product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cdr_allowed_curriculum",
        sa.Column("product_variant_id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["curriculum_id"], ["cdr_curriculum.id"]),
        sa.ForeignKeyConstraint(
            ["product_variant_id"],
            ["cdr_product_variant.id"],
        ),
        sa.PrimaryKeyConstraint("product_variant_id", "curriculum_id"),
    )
    op.create_table(
        "cdr_purchase",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("product_variant_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_variant_id"],
            ["cdr_product_variant.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("user_id", "product_variant_id"),
    )
    op.create_table(
        "cdr_action",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum(CdrLogActionType, name="cdrlogactiontype"),
            nullable=False,
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("timestamp", TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("cdr_purchase")
    op.drop_table("cdr_allowed_curriculum")
    op.drop_table("cdr_product_variant")
    op.drop_table("cdr_product_constraint")
    op.drop_table("cdr_document_constraint")
    op.drop_table("cdr_product")
    op.drop_index(
        op.f("ix_cdr_signature_signature_type"),
        table_name="cdr_signature",
    )
    op.drop_table("cdr_signature")
    op.drop_table("cdr_document")
    op.drop_table("cdr_seller")
    op.drop_index(
        op.f("ix_cdr_payment_payment_type"),
        table_name="cdr_payment",
    )
    op.drop_table("cdr_payment")
    op.drop_index(
        op.f("ix_cdr_membership_membership"),
        table_name="cdr_membership",
    )
    op.drop_table("cdr_membership")
    op.drop_table("cdr_curriculum_membership")
    
    op.drop_table("cdr_curriculum")
    op.drop_table("cdr_action")

    sa.Enum(AvailableMembership, name="availablemembership").drop(op.get_bind())
    sa.Enum(PaymentType, name="paymenttype").drop(op.get_bind())
    sa.Enum(DocumentSignatureType, name="documentsignaturetype").drop(op.get_bind())
    sa.Enum(CdrLogActionType, name="cdrlogactiontype").drop(op.get_bind())
    # ### end Alembic commands ###


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass
