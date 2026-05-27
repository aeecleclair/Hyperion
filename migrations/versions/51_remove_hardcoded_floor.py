"""Remove hardcoded floor

Create Date: 2025-11-30 01:50:06.674367
"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b04f76f4198f"
down_revision: str | None = "467ad07734c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class FloorsType(str, Enum):
    # WARNING: the key is used in the database. Use the same key and value.
    Autre = "Autre"
    Adoma = "Adoma"
    Exte = "Exte"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T56 = "T56"
    U1 = "U1"
    U2 = "U2"
    U3 = "U3"
    U4 = "U4"
    U56 = "U56"
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    V45 = "V45"
    V6 = "V6"
    X1 = "X1"
    X2 = "X2"
    X3 = "X3"
    X4 = "X4"
    X5 = "X5"
    X6 = "X6"


def upgrade() -> None:
    op.alter_column(
        "core_user",
        "floor",
        type_=sa.String(),
    )
    sa.Enum(FloorsType, name="floorstype", create_type=False).drop(op.get_bind())


def downgrade() -> None:
    sa.Enum(
        FloorsType,
        name="floorstype",
        create_type=True,
    ).create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "core_user",
        "floor",
        existing_type=sa.String(),
        type_=sa.Enum(FloorsType, name="floorstype"),
        postgresql_using="floor::text::floorstype",
    )


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
