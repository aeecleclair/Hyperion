import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.raid import schemas_raid
from app.modules.raid.endpoints_raid import set_security_file

# --- Helper functions -----------------------------------------------------


def _create_mock_db() -> AsyncMock:
    """Create a mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    # Mock the execute method to return a proper result
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.first.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _create_mock_user(user_id: str = "user_123") -> Mock:
    """Create a mock CoreUser for testing."""
    user = Mock()
    user.id = user_id
    user.name = "Test"
    user.firstname = "User"
    user.email = "test@example.com"
    user.phone = "+33123456789"
    user.birthday = datetime.date(1990, 1, 1)
    user.groups = []
    user.account_type = None
    return user


def _create_mock_edition() -> Mock:
    """Create a mock RaidEdition for testing."""
    edition = Mock(spec=schemas_raid.RaidEdition)
    edition.id = uuid4()
    edition.name = "Raid 2024"
    edition.year = 2024
    edition.active = True
    edition.inscription_enabled = True
    return edition


def _create_mock_team(team_id: str = "team_123") -> Mock:
    """Create a mock RaidTeam for testing."""
    team = Mock(spec=schemas_raid.RaidTeam)
    team.id = team_id
    return team


def _create_mock_participant(
    security_file_id: str | None = "sec_file_123",
    user_id: str = "user_123",
    edition_id: uuid4 | None = None,
) -> Mock:
    """Create a mock RaidParticipant for testing."""
    if edition_id is None:
        edition_id = uuid4()
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.user_id = user_id
    participant.edition_id = edition_id
    participant.security_file_id = security_file_id
    participant.status = "draft"
    participant.user = _create_mock_user(user_id)
    return participant


def _create_mock_security_file_base() -> schemas_raid.SecurityFileBase:
    """Create a mock SecurityFileBase for testing."""
    return schemas_raid.SecurityFileBase(
        allergy=None,
        asthma=False,
        intensive_care_unit=None,
        intensive_care_unit_when=None,
        ongoing_treatment=None,
        sicknesses=None,
        hospitalization=None,
        surgical_operation=None,
        trauma=None,
        family=None,
        emergency_person_firstname="Jane",
        emergency_person_name="Doe",
        emergency_person_phone="0600000000",
        file_id=None,
    )


# --- Tests for security file FK violation ----------------------------------


class TestSecurityFileFKViolation:
    """Tests to reproduce the FK violation when updating security file."""

    @pytest.mark.asyncio
    async def test_set_security_file_update_existing_success(self) -> None:
        """Test updating an existing security file works without FK violation."""
        db = _create_mock_db()
        user = _create_mock_user()
        edition = _create_mock_edition()
        team = _create_mock_team()
        participant = _create_mock_participant(security_file_id="existing_sec_file_id")
        security_file_base = _create_mock_security_file_base()

        # Mock the permission check
        with (
            patch("app.modules.raid.endpoints_raid.has_user_permission", new=AsyncMock(return_value=False)),
            patch("app.modules.raid.endpoints_raid.get_participant_or_404", new=AsyncMock(return_value=participant)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_team_by_participant_id", new=AsyncMock(return_value=team)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.update_security_file", new=AsyncMock()) as mock_update,
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_security_file_by_security_id", new=AsyncMock(return_value=Mock(spec=schemas_raid.SecurityFile, id="existing_sec_file_id"))),
        ):
            result = await set_security_file(
                security_file=security_file_base,
                participant_id="user_123",
                db=db,
                user=user,
                edition=edition,
            )

            # Verify update_security_file was called with correct ID
            mock_update.assert_called_once_with(
                security_file_id="existing_sec_file_id",
                security_file=security_file_base,
                db=db,
            )
            assert result is not None
            assert result.id == "existing_sec_file_id"

    @pytest.mark.asyncio
    async def test_set_security_file_create_new_when_none_exists(self) -> None:
        """Test creating a new security file when participant has none."""
        db = _create_mock_db()
        user = _create_mock_user()
        edition = _create_mock_edition()
        team = _create_mock_team()
        participant = _create_mock_participant(security_file_id=None)
        security_file_base = _create_mock_security_file_base()

        mock_security_file = Mock(spec=schemas_raid.SecurityFile)
        mock_security_file.id = "new_sec_file_id"

        with (
            patch("app.modules.raid.endpoints_raid.has_user_permission", new=AsyncMock(return_value=False)),
            patch("app.modules.raid.endpoints_raid.get_participant_or_404", new=AsyncMock(return_value=participant)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_team_by_participant_id", new=AsyncMock(return_value=team)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.add_security_file", new=AsyncMock()) as mock_add,
            patch("app.modules.raid.endpoints_raid.cruds_raid.assign_security_file", new=AsyncMock()) as mock_assign,
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_security_file_by_security_id", new=AsyncMock(return_value=mock_security_file)),
            patch("uuid.uuid4", return_value="new_sec_file_id"),
        ):
            result = await set_security_file(
                security_file=security_file_base,
                participant_id="user_123",
                db=db,
                user=user,
                edition=edition,
            )

            # Verify add_security_file was called
            mock_add.assert_called_once()
            # Verify assign_security_file was called
            mock_assign.assert_called_once_with(
                "user_123",
                edition.id,
                "new_sec_file_id",
                db,
            )
            assert result is mock_security_file

    @pytest.mark.asyncio
    async def test_set_security_file_update_preserves_participant_link(self) -> None:
        """Test that updating security file preserves the participant -> security_file link.

        This is the critical test - the FK violation happens when the update
        somehow breaks the link between participant.security_file_id and
        security_file.id.
        """
        db = _create_mock_db()
        user = _create_mock_user()
        edition = _create_mock_edition()
        team = _create_mock_team()
        security_file_id = "sec_file_123"
        participant = _create_mock_participant(security_file_id=security_file_id)
        security_file_base = _create_mock_security_file_base()

        with (
            patch("app.modules.raid.endpoints_raid.has_user_permission", new=AsyncMock(return_value=False)),
            patch("app.modules.raid.endpoints_raid.get_participant_or_404", new=AsyncMock(return_value=participant)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_team_by_participant_id", new=AsyncMock(return_value=team)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.update_security_file", new=AsyncMock()) as mock_update,
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_security_file_by_security_id", new=AsyncMock(return_value=Mock(spec=schemas_raid.SecurityFile, id=security_file_id))),
        ):
            await set_security_file(
                security_file=security_file_base,
                participant_id="user_123",
                db=db,
                user=user,
                edition=edition,
            )

            # The update should NOT change the security_file_id
            # It should only update the fields in SecurityFileBase
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args.kwargs["security_file_id"] == security_file_id
            assert call_args.kwargs["security_file"] == security_file_base
            assert call_args.kwargs["db"] == db

    @pytest.mark.asyncio
    async def test_update_security_file_does_not_change_id(self) -> None:
        """Test that update_security_file doesn't try to change the primary key.

        This is the potential bug - if update_security_file somehow includes
        the 'id' field in the update values, it would violate the FK because
        the participant still references the old ID.
        """

        # Create a SecurityFileBase with all fields
        security_file_base = schemas_raid.SecurityFileBase(
            allergy="pollen",
            asthma=True,
            intensive_care_unit=False,
            intensive_care_unit_when=None,
            ongoing_treatment="medication",
            sicknesses="asthma",
            hospitalization="none",
            surgical_operation="appendectomy",
            trauma="broken arm",
            family="heart disease",
            emergency_person_firstname="John",
            emergency_person_name="Smith",
            emergency_person_phone="0612345678",
            file_id="file_123",
        )

        # Check what model_dump returns
        dump = security_file_base.model_dump(exclude_none=True)
        assert "id" not in dump, "SecurityFileBase should not have 'id' field"
        assert "validation" not in dump, "SecurityFileBase should not have 'validation' field"
        # The dump should only contain the fields that are set
        assert dump["allergy"] == "pollen"
        assert dump["asthma"] is True
        assert dump["emergency_person_firstname"] == "John"

        # This test verifies the schema doesn't include id/validation
        # The actual cruds_raid.update_security_file uses this dump
        # So if the schema is correct, the update won't include id/validation


# --- Additional test for the FK violation scenario ---


class TestSecurityFileFKEdgeCases:
    """Edge cases that might trigger the FK violation."""

    @pytest.mark.asyncio
    async def test_multiple_participants_same_security_file(self) -> None:
        """Test scenario where multiple participants might reference same security file.

        This shouldn't normally happen (one-to-one), but if it does, updating
        the security file could affect multiple participants.
        """
        # This is more of a data integrity test - in normal operation,
        # each participant should have their own security file

    @pytest.mark.asyncio
    async def test_security_file_id_mismatch(self) -> None:
        """Test when participant.security_file_id doesn't match actual security file.

        This could happen if:
        1. A security file was deleted but participant still references it
        2. A race condition during creation
        """
        db = _create_mock_db()
        user = _create_mock_user()
        edition = _create_mock_edition()
        team = _create_mock_team()
        participant = _create_mock_participant(security_file_id="non_existent_sec_file")
        security_file_base = _create_mock_security_file_base()

        with (
            patch("app.modules.raid.endpoints_raid.has_user_permission", new=AsyncMock(return_value=False)),
            patch("app.modules.raid.endpoints_raid.get_participant_or_404", new=AsyncMock(return_value=participant)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_team_by_participant_id", new=AsyncMock(return_value=team)),
            patch("app.modules.raid.endpoints_raid.cruds_raid.update_security_file", new=AsyncMock()) as mock_update,
            patch("app.modules.raid.endpoints_raid.cruds_raid.get_security_file_by_security_id", new=AsyncMock(return_value=None)),
        ):
            mock_update.side_effect = Exception("FK violation: security file not found")
            with pytest.raises(Exception, match="FK violation"):
                await set_security_file(
                    security_file=security_file_base,
                    participant_id="user_123",
                    db=db,
                    user=user,
                    edition=edition,
                )

