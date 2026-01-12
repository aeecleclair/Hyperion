from pydantic import BaseModel


# <-- Contacts for PE5 SafetyCards 2025 -->
class ContactBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
# <--End of Contacts for PE5 SafetyCards 2025 -->
