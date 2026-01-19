import logging

import xlsxwriter

hyperion_error_logger = logging.getLogger("hyperion.error")


def generate_format(workbook: xlsxwriter.Workbook):
    def make_format(
        workbook: xlsxwriter.Workbook,
        *,
        color: str | None = None,
        bold: bool = False,
        align: str = "center",
        font: str = "Raleway",
        right: int | None = None,
        left: int | None = None,
        bottom: int | None = None,
        bg_color: str | None = None,
        font_color: str | None = None,
    ):
        fmt_dict: dict[str, str | int | bool] = {
            "align": align,
            "font_name": font,
        }
        if color:
            fmt_dict["font_color"] = color
        if font_color:
            fmt_dict["font_color"] = font_color
        if bg_color:
            fmt_dict["bg_color"] = bg_color
        if bold:
            fmt_dict["bold"] = True
        if right is not None:
            fmt_dict["right"] = right
        if left is not None:
            fmt_dict["right"] = left
        if bottom is not None:
            fmt_dict["bottom"] = bottom
        return workbook.add_format(fmt_dict)

    return {
        "header": {
            "base": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
            ),
            "right": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=1,
            ),
            "left": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                left=1,
            ),
            "left_right": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=1,
                left=1,
            ),
            "right_thick": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=2,
            ),
            "left_thick": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                left=2,
            ),
            "left_right_thick": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=2,
                left=2,
            ),
        },
        "validated": {
            "base": make_format(workbook, bold=True, font_color="green"),
            "right": make_format(workbook, bold=True, font_color="green", right=1),
            "thick": make_format(workbook, bold=True, font_color="green", right=2),
            "bottom": make_format(workbook, bold=True, font_color="green", bottom=2),
            "bottom_right": make_format(
                workbook,
                bold=True,
                font_color="green",
                bottom=2,
                right=1,
            ),
            "bottom_thick": make_format(
                workbook,
                bold=True,
                font_color="green",
                bottom=2,
                right=2,
            ),
        },
        "not_validated": {
            "base": make_format(workbook, bold=True, font_color="red"),
            "right": make_format(workbook, bold=True, font_color="red", right=1),
            "thick": make_format(workbook, bold=True, font_color="red", right=2),
            "bottom": make_format(workbook, bold=True, font_color="red", bottom=2),
            "bottom_right": make_format(
                workbook,
                bold=True,
                font_color="red",
                bottom=2,
                right=1,
            ),
            "bottom_thick": make_format(
                workbook,
                bold=True,
                font_color="red",
                bottom=2,
                right=2,
            ),
        },
        "other": {
            "base": make_format(workbook),
            "right": make_format(workbook, right=1),
            "thick": make_format(workbook, right=2),
            "bottom": make_format(workbook, bottom=2),
            "bottom_right": make_format(workbook, bottom=2, right=1),
            "bottom_thick": make_format(workbook, bottom=2, right=2),
        },
    }


def autosize_columns(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    columns_max_length: list[int],
):
    for i, length in enumerate(columns_max_length):
        worksheet.set_column(i, i, length + 3)
