"""empty message

Create Date: 2024-04-28 11:58:35.289610
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "875542976059"
down_revision: str | None = "d99516f0bbcb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "flappy-bird_score",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("creation_time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_flappy-bird_score_id"),
        "flappy-bird_score",
        ["id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_flappy-bird_score_id"), table_name="flappy-bird_score")
    op.drop_table("flappy-bird_score")
    # ### end Alembic commands ###
