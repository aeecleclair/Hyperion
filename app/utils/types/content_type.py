from enum import Enum


class ContentType(str, Enum):
    """
    Accepted `content_type` for files
    """

    jpg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"
    pdf = "application/pdf"
