import logging

from app.core.core_module_list import core_module_list
from app.modules.module_list import module_list
from app.types.module import CoreModule

hyperion_error_logger = logging.getLogger("hyperion.error")

all_module_list: list[CoreModule] = []
permissions_list: list[str] = []
full_name_permissions_list: list[str] = []

all_module_list.extend(module_list)
all_module_list.extend(core_module_list)

for module in all_module_list:
    if module.permissions:
        permissions_list.extend(
            module.permissions.__members__.keys(),
        )
        full_name_permissions_list.extend(
            [
                module.permissions.__name__ + "." + name
                for name in module.permissions.__members__
            ],
        )
