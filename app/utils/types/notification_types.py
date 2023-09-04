from enum import Enum


class Topic(str, Enum):
    """
    A list of topics. An user can suscribe to a topic to receive notifications about it.
    """

    cinema = "cinema"
    advert = "advert"
    bookingadmin = "bookingadmin"
    amap = "amap"
    booking = "booking"
    event = "event"
    loan = "loan"
    raffle = "raffle"
    vote = "vote"


class CustomTopic:
    def __init__(self, topic: Topic, topic_identifier: str | None = None):
        self.topic = topic
        self.topic_identifier = topic_identifier or ""

    def to_str(self):
        if self.topic_identifier:
            return f"{self.topic}_{self.topic_identifier}"
        else:
            return self.topic

    @classmethod
    def from_str(cls, topic_str: str):
        if "_" in topic_str:
            topic, topic_identifier = topic_str.split("_")
        else:
            topic = topic_str
            topic_identifier = None
        topic = Topic(topic)
        return cls(topic=topic, topic_identifier=topic_identifier)
