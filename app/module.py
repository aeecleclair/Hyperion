import importlib
import logging
from pathlib import Path

from app.types.module import CoreModule, Module

hyperion_error_logger = logging.getLogger("hyperion.error")

module_list: list[Module] = []
core_module_list: list[CoreModule] = []
all_modules: list[CoreModule] = []

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


for endpoints_file in Path().glob("app/core/*/endpoints_*.py"):
    endpoint_module = importlib.import_module(
        ".".join(endpoints_file.with_suffix("").parts),
    )
    if hasattr(endpoint_module, "core_module"):
        core_module: CoreModule = endpoint_module.core_module
        core_module_list.append(core_module)
    else:
        hyperion_error_logger.error(
            f"Core module {endpoints_file} does not declare a core module. It won't be enabled.",
        )

all_modules = module_list + core_module_list
