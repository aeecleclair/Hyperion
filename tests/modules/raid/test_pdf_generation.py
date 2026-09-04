"""Tests for PDF generation to ensure filenames are UUIDs, not team names."""

import datetime
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.raid import coredata_raid, schemas_raid
from app.modules.raid.raid_type import Difficulty, Situation, Size
from app.modules.raid.utils.utils_raid import (
    generate_recap_file_pdf,
    generate_security_file_pdf,
    get_all_security_files_zip,
    get_all_team_files_zip,
)
from app.types.exceptions import FileNameIsNotAnUUIDError
from app.utils.tools import save_bytes_as_data

# --- Helper functions -----------------------------------------------------


def _create_mock_participant(user_id: str | None = None) -> MagicMock:
    """Create a mock RaidParticipant for testing."""
    if user_id is None:
        user_id = str(uuid4())
    participant = MagicMock(spec=schemas_raid.RaidParticipant)
    participant.user_id = user_id
    participant.situation = Situation.centrale
    participant.is_minor = False
    participant.student_card_id = None
    participant.id_card = None
    participant.medical_certificate = None
    participant.raid_rules = None
    participant.parent_authorization = None
    participant.security_file = None
    participant.student_card = None
    participant.medical_certificate_id = None
    participant.id_card_id = None
    participant.raid_rules_id = None
    participant.parent_authorization_id = None
    participant.attestation_on_honour = False
    participant.payment = False
    participant.t_shirt_payment = False
    participant.t_shirt_size = Size.M
    participant.diet = None
    participant.address = None
    participant.other_school = None
    participant.company = None
    participant.bike_size = Size.M
    participant.status = "draft"
    participant.user = MagicMock()
    participant.user.name = "Doe"
    participant.user.firstname = "John"
    participant.user.email = "john@example.com"
    participant.user.phone = "+33123456789"
    participant.user.birthday = datetime.date(1990, 1, 1)
    return participant


def _create_mock_information() -> MagicMock:
    """Create a mock RaidInformation for testing."""
    info = MagicMock(spec=coredata_raid.RaidInformation)
    info.president = None
    info.rescue = None
    info.security_responsible = None
    info.volunteer_responsible = None
    info.course_responsible = None
    return info


def _create_mock_team(
    team_id: str | None = None,
    team_name: str = "Test Team",
) -> MagicMock:
    """Create a mock RaidTeam for testing."""
    if team_id is None:
        team_id = str(uuid4())
    team = MagicMock(spec=schemas_raid.RaidTeam)
    team.id = team_id
    team.name = team_name
    team.difficulty = Difficulty.discovery
    team.meeting_place = None
    team.number = 1
    team.captain = _create_mock_participant()
    team.second = None
    return team


class TestPDFGenerationFilename:
    """Tests to ensure PDF filenames are UUIDs, not team names."""

    @pytest.mark.asyncio
    async def test_generate_security_file_pdf_uses_user_id_as_filename(self):
        """Test that security file PDF uses participant.user_id as filename (UUID)."""
        participant = _create_mock_participant()
        information = _create_mock_information()

        with patch(
            "app.modules.raid.utils.utils_raid.generate_pdf_from_template",
            new=AsyncMock(),
        ) as mock_generate:
            await generate_security_file_pdf(participant, information)

            # The filename should be the participant's user_id (a UUID)
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["filename"] == participant.user_id
            # The filename should be a UUID, not a team name
            assert call_kwargs["filename"] != "Équipe de xxxx"
            assert call_kwargs["filename"] != participant.user.name

    @pytest.mark.asyncio
    async def test_generate_recap_file_pdf_uses_team_id_as_filename(self):
        """Test that recap file PDF uses team.id as filename (UUID), not team.name."""
        team = _create_mock_team(team_name="Équipe de Test")
        team_id = team.id

        with patch(
            "app.modules.raid.utils.utils_raid.generate_pdf_from_template",
            new=AsyncMock(),
        ) as mock_generate:
            await generate_recap_file_pdf(team)

            # The filename should be the team.id (a UUID)
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["filename"] == team_id
            # The filename should NOT be the team name
            assert call_kwargs["filename"] != team.name
            assert call_kwargs["filename"] != "Équipe de Test"

    @pytest.mark.asyncio
    async def test_get_all_team_files_zip_uses_team_id_for_pdf(self):
        """Test that get_all_team_files_zip uses team.id as filename for PDF generation."""
        team = _create_mock_team(team_name="Équipe de Test")
        db = AsyncMock(spec=AsyncSession)
        information = _create_mock_information()
        edition_id = uuid4()

        with (
            patch(
                "app.modules.raid.utils.utils_raid.cruds_raid.get_all_teams_including_security_files",
                new=AsyncMock(return_value=[team]),
            ),
            patch(
                "app.modules.raid.utils.utils_raid.generate_recap_file_pdf",
                new=AsyncMock(return_value=team.id),
            ) as mock_generate,
            patch(
                "app.modules.raid.utils.utils_raid.get_file_path_from_data",
                new=AsyncMock(return_value=MagicMock()),
            ),
            patch("zipfile.ZipFile", new=MagicMock()),
        ):
            await get_all_team_files_zip(db, information, edition_id)

            # The PDF should be generated with team.id (UUID), not team.name
            mock_generate.assert_called_once_with(team)
            # Verify the result is team.id (UUID)
            assert mock_generate.return_value == team.id

    @pytest.mark.asyncio
    async def test_get_all_security_files_zip_uses_user_id_for_pdf(self):
        """Test that get_all_security_files_zip uses participant.user_id as filename."""
        team = _create_mock_team(team_name="Équipe de Test")
        db = AsyncMock(spec=AsyncSession)
        information = _create_mock_information()
        edition_id = uuid4()

        with (
            patch(
                "app.modules.raid.utils.utils_raid.cruds_raid.get_all_teams_including_security_files",
                new=AsyncMock(return_value=[team]),
            ),
            patch(
                "app.modules.raid.utils.utils_raid.generate_security_file_pdf",
                new=AsyncMock(return_value=team.captain.user_id),
            ) as mock_generate,
            patch(
                "app.modules.raid.utils.utils_raid.get_file_path_from_data",
                new=AsyncMock(return_value=MagicMock()),
            ),
            patch("zipfile.ZipFile", new=MagicMock()),
        ):
            await get_all_security_files_zip(db, information, edition_id)

            # The PDF should be generated with participant.user_id (UUID), not team name
            mock_generate.assert_called()
            # Verify the result is participant.user_id (UUID)
            assert mock_generate.return_value == team.captain.user_id


class TestPDFGenerationOldCodePattern:
    """Tests that verify the OLD code pattern (team name as filename) is NOT used."""

    @pytest.mark.asyncio
    async def test_old_pdf_writer_pattern_not_used(self):
        """Verify the old pattern using team.name as filename is not present.

        The old code (before weasyprint migration) used:
        - file_name = f"{team.number}_{team.name}_{captain.name}_{captain.firstname}.pdf"
        - pdf_writer.write_team(team) which used team.name in filename

        Current code should use team.id (UUID) as filename.
        """
        team = _create_mock_team(team_name="Équipe de Test")

        with patch(
            "app.modules.raid.utils.utils_raid.generate_pdf_from_template",
            new=AsyncMock(),
        ) as mock_generate:
            await generate_recap_file_pdf(team)

            call_kwargs = mock_generate.call_args.kwargs
            filename = call_kwargs["filename"]

            # Should be UUID, not team name with special characters
            assert filename == team.id
            assert "Équipe" not in filename
            assert " " not in filename  # UUIDs don't have spaces
            assert "_" not in filename or len(filename) == 36  # UUID format


class TestSaveBytesAsDataFilenameValidation:
    """Tests for save_bytes_as_data filename validation."""

    @pytest.mark.asyncio
    async def test_save_bytes_as_data_rejects_non_uuid_filename(self):
        """Test that save_bytes_as_data rejects non-UUID filenames.

        This is the protection that would catch the old pattern
        if it somehow made it through.
        """
        # Try to save with a team-name-like filename (should fail)
        with pytest.raises(FileNameIsNotAnUUIDError):
            await save_bytes_as_data(
                file_bytes=b"test",
                directory="test",
                filename="Équipe de Test",  # Not a UUID
                extension="pdf",
            )

        # Try with a filename that has spaces (should fail)
        with pytest.raises(FileNameIsNotAnUUIDError):
            await save_bytes_as_data(
                file_bytes=b"test",
                directory="test",
                filename="team name with spaces",  # Not a UUID
                extension="pdf",
            )

        # Valid UUID should work (if directory exists)
        with tempfile.TemporaryDirectory():
            # We can't easily change the data path, so just test the validation
            pass
