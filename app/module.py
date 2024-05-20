import importlib
import logging
from pathlib import Path

from app.core.module import Module

hyperion_error_logger = logging.getLogger("hyperion.error")

module_list: list[Module] = []

for endpoints_file in Path().glob("app/modules/*/endpoints_*.py"):
    endpoint_module = importlib.import_module(
        ".".join(endpoints_file.with_suffix("").parts),
    )
    if hasattr(endpoint_module, "module"):
        module: Module = endpoint_module.module
        module_list.append(module)
    else:
        hyperion_error_logger.error(
            f"Module {endpoints_file} does not declare a module. It won't be enabled.",
        )
