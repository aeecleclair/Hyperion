"""empty message

Create Date: 2026-04-13 11:44:05.698432
"""

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3108c3bc5425"
down_revision: str | None = "e58ffcd6b9eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE seed_library_plants
        SET nb_seeds_envelope = 0
        WHERE nb_seeds_envelope IS NULL
        """,
    )
    op.alter_column(
        "seed_library_plants",
        "nb_seeds_envelope",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.execute(
        """
        UPDATE seed_library_plants
        SET confidential = FALSE
        WHERE confidential IS NULL
        """,
    )
    op.alter_column(
        "seed_library_plants",
        "confidential",
        existing_type=sa.BOOLEAN(),
        nullable=False,
    )
    op.execute(
        """
        UPDATE seed_library_species
        SET difficulty = 0
        WHERE difficulty IS NULL
        """,
    )
    op.alter_column(
        "seed_library_species",
        "difficulty",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.execute(
        """
        UPDATE seed_library_species
        SET species_type = 'other'
        WHERE species_type IS NULL
        """,
    )
    op.alter_column(
        "seed_library_species",
        "species_type",
        existing_type=postgresql.ENUM(
            "aromatic",
            "vegetables",
            "interior",
            "fruit",
            "cactus",
            "ornamental",
            "succulent",
            "other",
            name="speciestype",
        ),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "seed_library_species",
        "species_type",
        existing_type=postgresql.ENUM(
            "aromatic",
            "vegetables",
            "interior",
            "fruit",
            "cactus",
            "ornamental",
            "succulent",
            "other",
            name="speciestype",
        ),
        nullable=True,
    )
    op.alter_column(
        "seed_library_species",
        "difficulty",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        "seed_library_plants",
        "confidential",
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )
    op.alter_column(
        "seed_library_plants",
        "nb_seeds_envelope",
        existing_type=sa.INTEGER(),
        nullable=True,
    )


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    species_id = uuid.uuid4()
    plant_id = uuid.uuid4()

    # Insert species with NULL values (future NOT NULL fields)
    alembic_runner.insert_into(
        "seed_library_species",
        {
            "id": species_id,
            "prefix": "TST",
            "name": f"Test species {species_id}",
            "difficulty": None,  # will be backfilled to 0
            "card": None,
            "nb_seeds_recommended": None,
            "species_type": None,  # will be backfilled to 'other'
            "start_season": None,
            "end_season": None,
            "time_maturation": None,
        },
    )

    # Insert plant with NULL values (future NOT NULL fields)
    alembic_runner.insert_into(
        "seed_library_plants",
        {
            "id": plant_id,
            "reference": f"REF-{plant_id}",
            "state": "waiting",  # adjust if enum differs
            "species_id": species_id,
            "propagation_method": "seed",  # adjust if enum differs
            "nb_seeds_envelope": None,  # will be backfilled to 0
            "ancestor_id": None,
            "previous_note": None,
            "current_note": None,
            "borrower_id": None,
            "confidential": None,  # will be backfilled to False
            "nickname": None,
            "planting_date": None,
            "borrowing_date": None,
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass
