# from app.modules.cdr.types_cdr import CdrStatus
from datetime import UTC, datetime

from app.types.core_data import BaseCoreData

# class Status(BaseCoreData):
#     status: CdrStatus = CdrStatus.pending


class CdrYear(BaseCoreData):
    year: int = datetime.now(UTC).year
