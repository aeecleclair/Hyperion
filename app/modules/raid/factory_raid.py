"""Factory that seeds a default raid edition plus a sample team and volunteer.

Runs only when no RaidEdition exists yet (fresh install), mirroring the
sport_competition factory's ``should_run`` contract.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.core.groups.factory_groups import CoreGroupsFactory
from app.core.groups.models_groups import CoreGroup, CoreMembership
from app.core.permissions import cruds_permissions, schemas_permissions
from app.core.users import cruds_users
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.raid import cruds_raid, schemas_raid
from app.modules.raid.raid_type import (
    Difficulty,
    MeetingPlace,
    RaidRegistrationStatus,
    Situation,
    Size,
)
from app.types.factory import Factory

# Stable group UUID so `FACTORIES_DEMO_USERS` in config.yaml can reference it.
RAID_ADMIN_GROUP_ID = "7a1da1d0-0000-0000-0000-000000000001"
RAID_ADMIN_EMAIL = "admin@raid.test"


class RaidFactory(Factory):
    depends_on = [CoreUsersFactory, CoreGroupsFactory]

    edition_id = uuid.uuid4()
    team_id = str(uuid.uuid4())

    @classmethod
    async def should_run(cls, db: AsyncSession) -> bool:
        return await cruds_raid.get_all_editions(db) == []

    @classmethod
    async def _ensure_raid_admin_group(cls, db: AsyncSession) -> None:
        """Create the raid_admin group + permission and grant it to the
        admin demo user if config.yaml defined one."""
        raid_admin_group = CoreGroup(
            id=RAID_ADMIN_GROUP_ID,
            name="raid_admin",
            description="Raid organizers with manage_raid permission",
        )
        await cruds_groups.create_group(db=db, group=raid_admin_group)
        await cruds_permissions.create_group_permission(
            permission=schemas_permissions.CoreGroupPermission(
                permission_name="manage_raid",
                group_id=RAID_ADMIN_GROUP_ID,
            ),
            db=db,
        )

        admin_user = await cruds_users.get_user_by_email(
            db=db,
            email=RAID_ADMIN_EMAIL,
        )
        if admin_user is not None:
            await cruds_groups.create_membership(
                db=db,
                membership=CoreMembership(
                    group_id=RAID_ADMIN_GROUP_ID,
                    user_id=admin_user.id,
                    description=None,
                ),
            )

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cls._ensure_raid_admin_group(db)

        edition = schemas_raid.RaidEdition(
            id=cls.edition_id,
            year=datetime.now(UTC).year,
            name="Raid",
            start_date=None,
            end_date=None,
            registering_end_date=None,
            active=True,
            inscription_enabled=True,
        )
        await cruds_raid.create_edition(edition, db)

        seed_users = CoreUsersFactory.other_users_id[:3]
        if len(seed_users) < 3:
            return

        captain_id, second_id, volunteer_id = seed_users

        for idx, uid in enumerate((captain_id, second_id)):
            participant = schemas_raid.RaidParticipantCreate(
                user_id=uid,
                edition_id=cls.edition_id,
                status=RaidRegistrationStatus.submitted,
                address=f"{idx + 1} rue de la Doua",
                bike_size=Size.M,
                t_shirt_size=Size.M,
                situation=Situation.centrale,
                attestation_on_honour=True,
            )
            await cruds_raid.create_participant(participant, db)

        team = schemas_raid.RaidTeamCreate(
            id=cls.team_id,
            edition_id=cls.edition_id,
            name="Team Seed",
            difficulty=Difficulty.sports,
            captain_id=captain_id,
            second_id=second_id,
            meeting_place=MeetingPlace.centrale,
        )
        await cruds_raid.create_team(team, db)

        volunteer = schemas_raid.RaidVolunteerCreate(
            user_id=volunteer_id,
            edition_id=cls.edition_id,
            created_at=datetime.now(UTC),
            has_car=True,
            car_seats=4,
            is_parcours_helper=True,
        )
        await cruds_raid.create_volunteer(volunteer, db)
