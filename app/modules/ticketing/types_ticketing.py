
from enum import Enum


class TicketStatus(str, Enum):
    PENDING = "pending" # The ticket has been created but not yet confirmed or paid for.
    CONFIRMED = "confirmed" # The ticket has been confirmed and is valid for entry.
    CANCELLED = "cancelled" # The ticket has been cancelled.
