from datetime import UTC, datetime
from enum import Enum


class InconsistentData(Exception):
    def __init__(self, complement: str | None, *args: object) -> None:
        super().__init__(*args)
        self.complement = complement

    def __str__(self) -> str:
        if self.complement:
            return f"Inconsistent data: {self.complement}"
        return "Inconsistent data"


class UnauthorizedAction(Exception):
    def __str__(self) -> str:
        return "Unauthorized action"


class SportCategory(Enum):
    masculine = "masculine"
    feminine = "feminine"


class CompetitionGroupType(Enum):
    sport_manager = "sport_manager"
    schools_bds = "schools_bds"


class ProductPublicType(Enum):
    pompom = "pompom"
    fanfare = "fanfare"
    cameraman = "cameraman"
    athlete = "athlete"


class DefaultCoreData(Enum):
    challenge_year = datetime.now(tz=UTC).year
