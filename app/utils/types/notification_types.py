from enum import Enum


class Topic(str, Enum):
    """
    A list of topics. An user can suscribe to a topic to receive notifications about it.
    """

    cinema = "cinema"
