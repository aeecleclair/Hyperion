from datetime import UTC, datetime

from app.modules.cdr.types_cdr import CdrStatus
from app.types.core_data import BaseCoreData


class CdrYear(BaseCoreData):
    year: int = datetime.now(UTC).year


class Status(BaseCoreData):
    status: CdrStatus = CdrStatus.pending
