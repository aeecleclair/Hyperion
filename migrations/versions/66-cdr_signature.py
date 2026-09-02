"""empty message

Create Date: 2026-08-25 20:17:56.779228
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "320892a84fd8"
down_revision: str | None = "dd905b1f5f57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cdr_document",
        sa.Column("document_template_id", sa.Uuid(), nullable=False),
    )
    op.create_foreign_key(
        "cdr_document_document_template_document_template_id_fkey",
        "cdr_document",
        "document_template",
        ["document_template_id"],
        ["id"],
    )
    op.add_column("cdr_signature", sa.Column("validated", sa.Boolean(), nullable=False))
    op.alter_column(
        "cdr_signature",
        "numeric_signature_id",
        existing_type=sa.VARCHAR(),
        type_=sa.Uuid(),
        existing_nullable=True,
        postgresql_using="numeric_signature_id::uuid",
    )

    op.create_foreign_key(
        "cdr_signature_document_document_numeric_signature_id_fkey",
        "cdr_signature",
        "document_document",
        ["numeric_signature_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "cdr_signature_document_document_numeric_signature_id_fkey",
        "cdr_signature",
        type_="foreignkey",
    )

    op.alter_column(
        "cdr_signature",
        "numeric_signature_id",
        existing_type=sa.Uuid(),
        type_=sa.VARCHAR(),
        existing_nullable=True,
        postgresql_using="numeric_signature_id::text",
    )

    op.drop_column("cdr_signature", "validated")

    op.drop_constraint(
        "cdr_document_document_template_document_template_id_fkey",
        "cdr_document",
        type_="foreignkey",
    )

    op.drop_column("cdr_document", "document_template_id")


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
