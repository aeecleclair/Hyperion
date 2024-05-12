"""empty message

Create Date: 2024-05-08 13:59:14.980836
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "28b84e7a1310"
down_revision: str | None = "ec5d90c1a3c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "raid_security_file", sa.Column("file_id", sa.String(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("raid_security_file", "file_id")
    # ### end Alembic commands ###
