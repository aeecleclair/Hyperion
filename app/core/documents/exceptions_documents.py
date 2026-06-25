from uuid import UUID


class ElementTeamNotFoundError(Exception):
    """Raised when a team is not found in the database."""

    def __init__(self, team_id: UUID):
        self.team_id = team_id
        super().__init__(f"Team with ID {team_id} not found in the database.")
