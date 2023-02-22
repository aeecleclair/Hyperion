from enum import IntEnum


class ThreadPermission(IntEnum):
    """
    Permissions in a thread
    """

    SEND_MESSAGES = 0x1
    DELETE_MESSAGES = 0x2
    ADD_MEMBERS = 0x4
    REMOVE_MEMBERS = 0x8
    ADMINISTRATOR = 0x10
