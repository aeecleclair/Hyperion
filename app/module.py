import logging
from typing import TYPE_CHECKING

from app.core.core_module_list import core_module_list
from app.modules.module_list import module_list

if TYPE_CHECKING:
    from app.core.permissions.type_permissions import ModulePermissions
    from app.types.module import CoreModule

hyperion_error_logger = logging.getLogger("hyperion.error")


class DuplicatePermissionsError(Exception):
    def __init__(self, permissions: list[list[str]]):
        arranged_permissions = [
            f"    - '{permission[0].split('.')[1]}': {', '.join(permission)}"
            for permission in permissions
        ]
        super().__init__(
            "Duplicate permissions name found in modules:\n"
            + "\n".join(arranged_permissions),
        )


all_module_list: list["CoreModule"] = []
all_module_list.extend(module_list)
all_module_list.extend(core_module_list)


permissions_list: list["ModulePermissions"] = []
full_name_permissions_list: list[str] = []
for module in all_module_list:
    if module.permissions:
        permissions_list.extend(
            module.permissions.__members__.values(),
        )
        full_name_permissions_list.extend(
            [
                module.permissions.__name__ + "." + name
                for name in module.permissions.__members__
            ],
        )
if len(set(permissions_list)) != len(permissions_list):
    duplicates = list({x for x in permissions_list if permissions_list.count(x) > 1})
    full_name_duplicates = [
        [name for name in full_name_permissions_list if name.split(".")[1] == duplicate]
        for duplicate in duplicates
    ]
    hyperion_error_logger.error(
        "Duplicate permissions found in modules: %s",
        full_name_duplicates,
    )
    raise DuplicatePermissionsError(full_name_duplicates)
