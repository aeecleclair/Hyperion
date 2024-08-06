"""7-visibility

Revision ID: 7e8b1b7c2f4a
Revises: 6afc765adaa2
Create Date: 2024-03-16 14:01:13.392655

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e8b1b7c2f4a"
down_revision: str | None = "e3d06397960d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "module_awareness",
        sa.Column("root", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("root"),
    )

    conn = op.get_bind()
    visibility_t = sa.Table(
        "module_visibility",
        sa.MetaData(),
        sa.Column("root", sa.String),
        sa.Column("allowed_group_id", sa.String),
        autoload_with=conn,
    )
    awareness_t = sa.Table(
        "module_awareness",
        sa.MetaData(),
        sa.Column("root", sa.String),
        autoload_with=conn,
    )

    visibilities = conn.execute(visibility_t.select()).fetchall()
    for visibility in visibilities:
        conn.execute(
            awareness_t.insert().values(
                root=visibility[0],
            ),
        )


def downgrade() -> None:
    op.drop_table("module_awareness")
