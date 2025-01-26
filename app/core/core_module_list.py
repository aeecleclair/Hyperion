import importlib
import logging
from pathlib import Path

from app.types.module import CoreModule

hyperion_error_logger = logging.getLogger("hyperion.error")

core_module_list: list[CoreModule] = []

for endpoints_file in Path().glob("app/core/*/endpoints_*.py"):
    endpoint = importlib.import_module(
        ".".join(endpoints_file.with_suffix("").parts),
    )
    if hasattr(endpoint, "core_module"):
        core_module: CoreModule = endpoint.core_module
        core_module_list.append(core_module)
    else:
        hyperion_error_logger.error(
            f"Core Module {endpoints_file} does not declare a module. It won't be enabled.",
        )
