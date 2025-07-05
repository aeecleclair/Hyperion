import asyncio
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from app.dependencies import get_settings
from app.types.sqlalchemy import Base
from app.utils.state import init_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    # Don't disable existing loggers
    # See https://stackoverflow.com/questions/42427487/using-alembic-config-main-redirects-log-output
    # We could in the future use Hyperion loggers for Alembic
    fileConfig(config.config_file_name, disable_existing_loggers=False)


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# This allows alembic to find our models and take them into account when generating migrations (do not remove)
for models_file in Path().glob("app/**/models_*.py"):
    __import__(".".join(models_file.with_suffix("").parts))

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # We don't want our custom type to be prefixed by the whole module path `app.types.datetime.`
        # because we don't want to have to import it in the migration file.
        # See https://alembic.sqlalchemy.org/en/latest/autogenerate.html#controlling-the-module-prefix
        user_module_prefix="",
    )

    with context.begin_transaction():
        context.run_migrations()


async def create_async_engine_and_run_async_migrations() -> None:
    """
    In this scenario we need to create an AsyncEngine and then obtain a AsyncConnection from it.
    We then call the `run_async_migrations` function to run the migrations.
    """

    # If we don't have a connection, we can safely assume that Hyperion is not running
    # Migrations should have been called from the CLI. We thus want to point to the production database
    # As we want to use the production database, we can call the `get_settings` function directly
    # instead of using it as a dependency (`app.dependency_overrides.get(get_settings, get_settings)()`)
    settings = get_settings()
    connectable = init_engine(settings)

    async with connectable.connect() as connection:
        await run_async_migrations(connection)
    await connectable.dispose()


async def run_async_migrations(connection: AsyncConnection) -> None:
    """ """
    # WARNING: SQLAlchemy does not support `Inspection on an AsyncConnection`. The call to Alembic must be wrapped in a `run_sync` call.
    # See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.
    await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    If a Connection or an AsyncConnection is not provided we may assume we are not in an existing event loop (ie. alembic was invoking from the cli).
    We create a new event loop and run the migrations asynchronously in it.
    WARNING: as we assume Alembic was invoked from the CLI, we want to point to the production settings (including the production database).

    If an async connection is already present in the context config, it means that alembic was invoked programmatically.
    We create a new event loop and run the migrations asynchronously in it.
    NOTE: since SQLAlchemy does not support `Inspection on an AsyncConnection`, we will wrap the call to Alembic in a `run_sync` call.

    If a synchronous connection is present in the context config, we can call the migration directly in the existing event loop.

    This `connection` attributes should be set when invoking alembic programmatically:
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#connection-sharing

    NOTE: many documentation are confuse and use the terms *connection* (`Connection` or `AsyncConnection`) and *connectable* (`Engine` or `AsyncEngine`) interchangeably.
    We requires a *connection* (`Connection` or `AsyncConnection`) object. You may obtain one from an *connectable* calling the [`connect` method](https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Engine.connect).
    """

    connection: None | Connection | AsyncConnection = config.attributes.get(
        "connection",
        None,
    )

    if connection is None:
        asyncio.run(create_async_engine_and_run_async_migrations())
    elif isinstance(connection, AsyncConnection):
        asyncio.run(run_async_migrations(connection))
    elif isinstance(connection, Connection):
        do_run_migrations(connection)
    else:
        raise TypeError(  # noqa: TRY003
            f"Unsupported connection object {connection}. A Connection or and AsyncConnection is required, got a {type(connection)}",
        )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
