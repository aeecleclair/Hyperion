"""change primary key type from string to UUID

Create Date: 2024-04-21 02:08:19.548067
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d99516f0bbcb"
down_revision: str | None = "e3d06397960d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "recommendation",
        "id",
        type_=sa.types.Uuid(),
        postgresql_using="id::uuid",
    )


def downgrade() -> None:
    op.alter_column(
        "recommendation",
        "id",
        type_=sa.types.String(),
    )
