from typing import Any
from uuid import UUID


class ElementTeamNotFoundError(Exception):
    """Raised when a team is not found in the database."""

    def __init__(self, team_id: UUID):
        self.team_id = team_id
        super().__init__(f"Team with ID {team_id} not found in the database.")


class ElementTemplateNotFoundError(Exception):
    """Raised when a template is not found in the database."""

    def __init__(self, template_id: UUID):
        self.template_id = template_id
        super().__init__(f"Template with ID {template_id} not found in the database.")


class MissingDocumensoURLError(Exception):
    """Raised when the documenso URL is missing in the configuration"""

    def __init__(self):
        super().__init__("Missing documenso URL in the configuration.")


class PayloadParsingError(Exception):
    """Raised when there is an error parsing the payload."""

    def __init__(self, body: Any, error: str):
        self.body = body
        self.error = error
        super().__init__(f"Error parsing payload: {error}.\nBody: {body}")
