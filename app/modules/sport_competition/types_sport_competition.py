from datetime import UTC, datetime
from enum import Enum
from typing import Literal


class InconsistentData(Exception):
    def __init__(self, complement: str | None, *args: object) -> None:
        super().__init__(*args)
        self.complement = complement

    def __str__(self) -> str:
        if self.complement:
            return f"Inconsistent data: {self.complement}"
        return "Inconsistent data"


class InvalidUserType(Exception):
    def __init__(self, complement: Literal["too_many", "none"], *args: object) -> None:
        super().__init__(*args)
        self.complement: Literal["too_many", "none"] = complement

    def __str__(self) -> str:
        if self.complement == "too_many":
            return "Invalid user type: too many types selected"
        return "Invalid user type: no type selected"


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


class ProductSchoolType(Enum):
    centrale = "centrale"
    from_lyon = "from_lyon"
    others = "others"


class DefaultCoreData(Enum):
    challenge_year = datetime.now(tz=UTC).year
