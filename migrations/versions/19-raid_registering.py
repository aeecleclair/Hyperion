"""empty message

Create Date: 2024-05-16 15:10:24.610001
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d7d834743d1"
down_revision: str | None = "5d05a19f14bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    document_validation = sa.Enum(
        "pending",
        "accepted",
        "refused",
        "temporary",
        name="documentvalidation",
    )
    document_type = sa.Enum(
        "idCard",
        "medicalCertificate",
        "studentCard",
        "raidRules",
        "parentAuthorization",
        name="documenttype",
    )
    size = sa.Enum("XS", "S", "M", "L", "XL", name="size")
    difficulty = sa.Enum("discovery", "sports", "expert", name="difficulty")
    meeting_place = sa.Enum("centrale", "bellecour", "anyway", name="meetingplace")

    op.create_table(
        "raid_document",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("uploaded_at", sa.Date(), nullable=False),
        sa.Column(
            "validation",
            document_validation,
            nullable=False,
        ),
        sa.Column(
            "type",
            document_type,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raid_document_id"), "raid_document", ["id"], unique=False)
    op.create_table(
        "raid_security_file",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("allergy", sa.String(), nullable=True),
        sa.Column("asthma", sa.Boolean(), nullable=False),
        sa.Column("intensive_care_unit", sa.Boolean(), nullable=True),
        sa.Column("intensive_care_unit_when", sa.String(), nullable=True),
        sa.Column("ongoing_treatment", sa.String(), nullable=True),
        sa.Column("sicknesses", sa.String(), nullable=True),
        sa.Column("hospitalization", sa.String(), nullable=True),
        sa.Column("surgical_operation", sa.String(), nullable=True),
        sa.Column("trauma", sa.String(), nullable=True),
        sa.Column("family", sa.String(), nullable=True),
        sa.Column("emergency_person_firstname", sa.String(), nullable=True),
        sa.Column("emergency_person_name", sa.String(), nullable=True),
        sa.Column("emergency_person_phone", sa.String(), nullable=True),
        sa.Column("file_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_raid_security_file_id"),
        "raid_security_file",
        ["id"],
        unique=False,
    )
    op.create_table(
        "raid_participant",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("firstname", sa.String(), nullable=False),
        sa.Column("birthday", sa.Date(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "bike_size",
            size,
            nullable=True,
        ),
        sa.Column(
            "t_shirt_size",
            size,
            nullable=True,
        ),
        sa.Column("situation", sa.String(), nullable=True),
        sa.Column("other_school", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("diet", sa.String(), nullable=True),
        sa.Column("id_card_id", sa.String(), nullable=True),
        sa.Column("medical_certificate_id", sa.String(), nullable=True),
        sa.Column("security_file_id", sa.String(), nullable=True),
        sa.Column("student_card_id", sa.String(), nullable=True),
        sa.Column("raid_rules_id", sa.String(), nullable=True),
        sa.Column("parent_authorization_id", sa.String(), nullable=True),
        sa.Column("attestation_on_honour", sa.Boolean(), nullable=False),
        sa.Column("payment", sa.Boolean(), nullable=False),
        sa.Column("is_minor", sa.Boolean(), nullable=False),
        sa.Column(
            "t_shirt_payment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(["id_card_id"], ["raid_document.id"]),
        sa.ForeignKeyConstraint(["medical_certificate_id"], ["raid_document.id"]),
        sa.ForeignKeyConstraint(["parent_authorization_id"], ["raid_document.id"]),
        sa.ForeignKeyConstraint(["raid_rules_id"], ["raid_document.id"]),
        sa.ForeignKeyConstraint(["security_file_id"], ["raid_security_file.id"]),
        sa.ForeignKeyConstraint(["student_card_id"], ["raid_document.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_raid_participant_id"),
        "raid_participant",
        ["id"],
        unique=False,
    )
    op.create_table(
        "raid_team",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column(
            "difficulty",
            difficulty,
            nullable=True,
        ),
        sa.Column("captain_id", sa.String(), nullable=False),
        sa.Column("second_id", sa.String(), nullable=True),
        sa.Column(
            "meeting_place",
            meeting_place,
            nullable=True,
        ),
        sa.Column("file_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["captain_id"], ["raid_participant.id"]),
        sa.ForeignKeyConstraint(["second_id"], ["raid_participant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raid_team_id"), "raid_team", ["id"], unique=False)
    op.create_table(
        "raid_invite",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["raid_team.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raid_invite_id"), "raid_invite", ["id"], unique=False)
    op.create_table(
        "raid_participant_checkout",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.Column("checkout_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["checkout_id"], ["payment_checkout.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["raid_participant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_raid_participant_checkout_id"),
        "raid_participant_checkout",
        ["id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    document_validation = sa.Enum(
        "pending",
        "accepted",
        "refused",
        "temporary",
        name="documentvalidation",
    )
    document_type = sa.Enum(
        "idCard",
        "medicalCertificate",
        "studentCard",
        "raidRules",
        "parentAuthorization",
        name="documenttype",
    )
    size = sa.Enum("XS", "S", "M", "L", "XL", name="size")
    difficulty = sa.Enum("discovery", "sports", "expert", name="difficulty")
    meeting_place = sa.Enum("centrale", "bellecour", "anyway", name="meetingplace")

    op.drop_index(op.f("ix_raid_invite_id"), table_name="raid_invite")
    op.drop_table("raid_invite")
    op.drop_index(op.f("ix_raid_team_id"), table_name="raid_team")
    op.drop_table("raid_team")
    op.drop_index(op.f("ix_raid_participant_id"), table_name="raid_participant")
    op.drop_index(op.f("ix_raid_security_file_id"), table_name="raid_security_file")
    op.drop_table("raid_security_file")
    op.drop_index(op.f("ix_raid_document_id"), table_name="raid_document")
    op.drop_table("raid_document")
    document_validation.drop(op.get_bind(), checkfirst=False)
    document_type.drop(op.get_bind(), checkfirst=False)
    size.drop(op.get_bind(), checkfirst=False)
    difficulty.drop(op.get_bind(), checkfirst=False)
    meeting_place.drop(op.get_bind(), checkfirst=False)
    op.drop_index(
        op.f("ix_raid_participant_checkout_id"),
        table_name="raid_participant_checkout",
    )
    op.drop_table("raid_participant_checkout")
    op.drop_table("raid_participant")

    # ### end Alembic commands ###


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
