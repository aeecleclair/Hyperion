"""70-raid-information-document-type

Add the `raidInformation` value to the `documenttype` enum (raid guide /
information documents uploaded by admins).

Create Date: 2026-09-22 00:05:12.000000
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1c2d3a4f5"
down_revision: str | None = "cfdbcbca654a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The new enum label, as declared in app.modules.raid.raid_type.DocumentType.
NEW_LABEL = "raidInformation"


def upgrade() -> None:
    # Postgres enums cannot be extended through SQLAlchemy types: add the
    # label directly. Appending is safe (never reorders or removes values).
    conn = op.get_bind()
    existing = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_enum "
            "JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
            "WHERE pg_type.typname = 'documenttype' AND pg_enum.enumlabel = :label",
        ),
        {"label": NEW_LABEL},
    ).fetchone()
    if existing is None:
        conn.execute(
            sa.text(
                f"ALTER TYPE documenttype ADD VALUE '{NEW_LABEL}'",
            ),
        )


def downgrade() -> None:
    # Postgres cannot remove an enum value without rebuilding the type and
    # every column using it; the label is harmless, so downgrading is a no-op
    # (matching the "additive enum value" convention).
    pass


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    """Verify the raidInformation label exists after the upgrade."""

    labels = {
        row[0]
        for row in alembic_connection.execute(
            sa.text("SELECT unnest(enum_range(NULL::documenttype))"),
        ).fetchall()
    }
    assert NEW_LABEL in labels
