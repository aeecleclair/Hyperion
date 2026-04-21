from enum import StrEnum

from app.types.exceptions import UnknownContentTypeExtensionError


class ContentType(StrEnum):
    """
    Accepted `content_type` for files
    """

    jpg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"
    pdf = "application/pdf"

    @property
    def extension(self) -> str:
        """
        Get the file extension corresponding to the content type
        """
        if self == ContentType.jpg:
            return "jpg"
        if self == ContentType.png:
            return "png"
        if self == ContentType.webp:
            return "webp"
        if self == ContentType.pdf:
            return "pdf"
        raise UnknownContentTypeExtensionError(content_type=self.value)

    def __str__(self):
        return self.extension


class PillowImageFormat(StrEnum):
    """
    Accepted image formats for Pillow
    """

    jpg = "JPEG"
    png = "PNG"
    webp = "WEBP"
