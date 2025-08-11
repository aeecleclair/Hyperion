from datetime import UTC, datetime

from app.types.core_data import BaseCoreData


class CdrYear(BaseCoreData):
    year: int = datetime.now(UTC).year
