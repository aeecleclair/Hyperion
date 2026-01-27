"""empty message

Create Date: 2025-12-08 11:28:24.682540
"""

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from app.types.content_type import PillowImageFormat
from app.utils.tools import compress_image

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1ec573d854a1"
down_revision: str | None = "ecd89212ca0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

data_sources: dict[str, dict[str, int]] = {
    "associations/logos": {
        "height": 300,
        "width": 300,
        "quality": 85,
    },
    "groups/logos": {
        "height": 300,
        "width": 300,
        "quality": 85,
    },
    "profile-pictures": {
        "height": 300,
        "width": 300,
        "quality": 85,
    },
    "adverts": {
        "height": 315,
        "width": 851,
        "quality": 85,
        "fit": 1,
    },
    "event": {
        "height": 315,
        "width": 851,
        "quality": 85,
        "fit": 1,
    },
    "campaigns": {
        "height": 300,
        "width": 300,
        "quality": 85,
    },
    "cinemasessions": {
        "height": 750,
        "width": 500,
        "quality": 85,
        "fit": 1,
    },
    "recommendations": {
        "height": 300,
        "width": 300,
        "quality": 85,
    },
}


def upgrade() -> None:
    for data_folder, params in data_sources.items():
        print("__________________________________________")  # noqa: T201
        print(f"Processing folder: {data_folder}")  # noqa: T201
        height = params.get("height")
        width = params.get("width")
        quality = params.get("quality", 85)
        fit = bool(params.get("fit", 0))
        if Path("data/" + data_folder).exists():
            for file_path in Path("data/" + data_folder).iterdir():
                print(" - ", file_path)  # noqa: T201
                if file_path.suffix in (".png", ".jpg", ".webp"):
                    with Path(file_path).open("rb") as file:
                        file_bytes = file.read()

                        Path(f"data/{data_folder}/original/").mkdir(
                            parents=True,
                            exist_ok=True,
                        )

                        # Save the original file
                        with Path(f"data/{data_folder}/original/{file_path.name}").open(
                            "wb",
                        ) as out_file:
                            out_file.write(file_bytes)

                        # Compress and save the image
                        res = compress_image(
                            file_bytes,
                            height=height,
                            width=width,
                            quality=quality,
                            output_format=PillowImageFormat.webp,
                            fit=fit,
                        )

                        # Delete the original file
                        Path(f"data/{data_folder}/{file_path.name}").unlink()

                        with Path(f"data/{data_folder}/{file_path.stem}.webp").open(
                            "wb",
                        ) as out_file:
                            out_file.write(res)


def downgrade() -> None:
    pass


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass
