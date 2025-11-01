"""empty message

Create Date: 2025-07-26 18:06:00.966810
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.types.sqlalchemy import TZDateTime

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "52ce74575f"
down_revision: str | None = "d1079d6b8e6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

structure_table = sa.Table(
    "myeclpay_structure",
    sa.MetaData(),
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("short_id", sa.String(), nullable=True, unique=True),
    sa.Column("siege_address_street", sa.String(), nullable=True),
    sa.Column("siege_address_city", sa.String(), nullable=True),
    sa.Column("siege_address_zipcode", sa.String(), nullable=True),
    sa.Column("siege_address_country", sa.String(), nullable=True),
    sa.Column("siret", sa.String(), nullable=True),
    sa.Column("iban", sa.String(), nullable=True),
    sa.Column("bic", sa.String(), nullable=True),
    sa.Column("creation", TZDateTime(), nullable=True),
)

store_table = sa.Table(
    "myeclpay_store",
    sa.MetaData(),
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("creation", TZDateTime(), nullable=True),
)


def upgrade() -> None:
    op.create_table(
        "myeclpay_withdrawal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("creation", TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "myeclpay_invoice",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("creation", TZDateTime(), nullable=False),
        sa.Column("start_date", TZDateTime(), nullable=False),
        sa.Column("end_date", TZDateTime(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("received", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["structure_id"],
            ["myeclpay_structure.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_table(
        "myeclpay_invoice_detail",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["myeclpay_invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["myeclpay_store.id"],
        ),
        sa.PrimaryKeyConstraint("invoice_id", "store_id"),
    )
    op.add_column(
        "myeclpay_store",
        sa.Column("creation", TZDateTime(), nullable=True),
    )
    op.add_column(
        "myeclpay_structure",
        sa.Column("short_id", sa.String(), nullable=True),
    )
    op.add_column(
        "myeclpay_structure",
        sa.Column("siege_address_street", sa.String(), nullable=True),
    )
    op.add_column(
        "myeclpay_structure",
        sa.Column("siege_address_city", sa.String(), nullable=True),
    )
    op.add_column(
        "myeclpay_structure",
        sa.Column("siege_address_zipcode", sa.String(), nullable=True),
    )
    op.add_column(
        "myeclpay_structure",
        sa.Column("siege_address_country", sa.String(), nullable=True),
    )
    op.add_column("myeclpay_structure", sa.Column("siret", sa.String(), nullable=True))
    op.add_column("myeclpay_structure", sa.Column("iban", sa.String(), nullable=True))
    op.add_column("myeclpay_structure", sa.Column("bic", sa.String(), nullable=True))
    op.add_column(
        "myeclpay_structure",
        sa.Column("creation", TZDateTime(), nullable=True),
    )
    op.create_unique_constraint(None, "myeclpay_structure", ["short_id"])
    conn = op.get_bind()
    conn.execute(
        sa.update(
            structure_table,
        ).values(
            {
                "siege_address_street": "To change",
                "siege_address_city": "To change",
                "siege_address_zipcode": "To change",
                "siege_address_country": "To change",
                "siret": None,
                "iban": "To change",
                "bic": "To change",
                "creation": datetime(2025, 6, 1, tzinfo=UTC),
            },
        ),
    )
    conn.execute(
        sa.update(
            store_table,
        ).values(
            {
                "creation": datetime(2025, 6, 1, tzinfo=UTC),
            },
        ),
    )
    op.alter_column(
        "myeclpay_store",
        "creation",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "creation",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "short_id",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "siege_address_street",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "siege_address_city",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "siege_address_zipcode",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "siege_address_country",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "iban",
        nullable=False,
    )
    op.alter_column(
        "myeclpay_structure",
        "bic",
        nullable=False,
    )

    # ### end Alembic commands ###s


def downgrade() -> None:
    op.drop_table("myeclpay_invoice_detail")
    op.drop_table("myeclpay_invoice")
    op.drop_table("myeclpay_withdrawal")
    op.drop_column("myeclpay_structure", "creation")
    op.drop_column("myeclpay_structure", "bic")
    op.drop_column("myeclpay_structure", "iban")
    op.drop_column("myeclpay_structure", "siret")
    op.drop_column("myeclpay_structure", "siege_address_country")
    op.drop_column("myeclpay_structure", "siege_address_zipcode")
    op.drop_column("myeclpay_structure", "siege_address_city")
    op.drop_column("myeclpay_structure", "siege_address_street")
    op.drop_column("myeclpay_structure", "short_id")
    op.drop_column("myeclpay_store", "creation")


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
