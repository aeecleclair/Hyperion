"""recommendation

Revision ID: d233bd29c521
Revises: f17e6182b0a9
Create Date: 2024-02-23 19:12:25.372249

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d233bd29c521"
down_revision: Union[str, None] = "f17e6182b0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "recommendation",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("creation", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("recommendation")
    # ### end Alembic commands ###
