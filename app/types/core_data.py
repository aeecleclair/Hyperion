from pydantic import BaseModel


class BaseCoreData(BaseModel):
    """
    A base model for core data class.

    Core data functionalities should be used when you need to store an unique row in the database.
    A typical use case is to store settings or configuration state for a module. If you need multiple rows, use a dedicated table.

    To use this class, you need to subclass it and define the fields you want to store in the database.
    Exemple:
    ```python
    class ExempleCoreData(BaseCoreData):
        name: str = "default"
        age: int = 18
    ```

    Then, you can use the `get_core_data` and `set_core_data` utils to interact with the database.
    ```python
    # Note: we pass the class object directly, and not an instance: `ExempleCoreData`
    core_data: ExempleCoreData = await get_core_data(ExempleCoreData)

    # Note: we pass an instance of the class, containing the data we want to store: `new_exemple_core_data`
    new_exemple_core_data: ExempleCoreData = ExempleCoreData(name="Fabristpp", age=42)
    await set_core_data(new_exemple_core_data)
    ```

    We you set core data, the content of the instance will be serialized to JSON and stored in the database,
    associated with the key corresponding to the name of your class.
    NOTE: the name of your class should thus be unique. We suggest to use the module name as prefix to avoid conflicts: ModuleCoreData, or ModuleMyDataNameCoreData.

    When you get core data, the JSON data will be deserialized using the class.

    When getting the data, if it does not exist in the database, a new instance of the class will be created.
    If you want to set default values, you can set them in the class definition:
    ```python
    class DefaultValueCoreData(BaseCoreData):
        name: str = "Default name"
    ```
    If you prefer a CoreDataNotFoundError to be raised when the data is not found in the database, just don't set default parameters.
    ```python
    class DefaultValueCoreData(BaseCoreData):
        name: str
    ```

    NOTE: making modifications to a CoreData class will usually require a migration to update the data in the database.
    """
