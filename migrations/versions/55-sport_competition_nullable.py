"""empty message

Create Date: 2025-10-21 19:53:38.521697
"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "562adbd796ae"
down_revision: str | None = "e81453aa7341"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class PaiementMethodType(Enum):
    manual = "manual"
    helloasso = "helloasso"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
        UPDATE competition_match
        SET date = NOW()
        WHERE date IS NULL
        """),
    )
    conn.execute(
        sa.text("""
        DELETE FROM competition_school_product_quota
        WHERE quota IS NULL
        """),
    )
    conn.execute(
        sa.text("""
        DELETE FROM competition_user
        WHERE is_athlete IS FALSE and is_pompom IS FALSE and is_cameraman IS FALSE and is_fanfare IS FALSE
        """),
    )
    op.alter_column("competition_match", "date", nullable=False)
    op.alter_column(
        "competition_school_product_quota",
        "quota",
        nullable=False,
    )
    sa.Enum(
        PaiementMethodType,
        name="paiementmethodtype",
    ).create(op.get_bind(), checkfirst=True)
    op.add_column(
        "competition_payment",
        sa.Column(
            "method",
            sa.Enum(
                PaiementMethodType,
                name="paiementmethodtype",
            ),
            nullable=False,
            server_default="helloasso",
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "competition_school_product_quota",
        "quota",
        nullable=True,
    )
    op.alter_column("competition_match", "date", nullable=True)
    op.drop_column("competition_payment", "method")
    sa.Enum(
        PaiementMethodType,
        name="paiementmethodtype",
    ).drop(op.get_bind(), checkfirst=True)


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
