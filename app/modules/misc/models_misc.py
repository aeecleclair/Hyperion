from datetime import datetime

from sqlalchemy.orm import Mapped

from app.types.sqlalchemy import Base, PrimaryKey


# <-- Contacts for PE5 -->
class Contacts(Base):
    __tablename__ = "misc_contacts"

    id: Mapped[PrimaryKey]
    creation: Mapped[datetime]
    name: Mapped[str]
    email: Mapped[str | None]
    phone: Mapped[str | None]
    location: Mapped[str | None]

# <-- End of contacts PE5 -->
