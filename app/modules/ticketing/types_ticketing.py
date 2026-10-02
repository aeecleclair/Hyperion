from enum import StrEnum


class TicketStatus(StrEnum):
    PENDING = (
        "pending"  # The ticket has been created but not yet confirmed or paid for.
    )
    CONFIRMED = "confirmed"  # The ticket has been confirmed and is valid for entry.
    CANCELLED = "cancelled"  # The ticket has been cancelled.
