from uuid import UUID


class ElementTeamNotFoundError(Exception):
    """Raised when a team is not found in the database."""

    def __init__(self, team_id: UUID):
        self.team_id = team_id
        super().__init__(f"Team with ID {team_id} not found in the database.")


class ElementTemplateNotFoundError(Exception):
    """Raised when a team is not found in the database."""

    def __init__(self, template_id: UUID):
        self.template_id = template_id
        super().__init__(f"Template with ID {template_id} not found in the database.")
