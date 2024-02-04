import asyncio
from logging.config import fileConfig
from sqlalchemy.engine import Connection
from app.dependencies import get_db_engine, get_settings
from alembic import context
from app.database import Base

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

# models_files = [x for x in os.listdir("./app/models") if re.match("models*", x)]
# for models_file in models_files:
#     __import__(f"app.models.{models_file[:-3]}")

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
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    If a connection is already present in the context config,
    we will use it instead of creating a new one.
    This connection should be set when invoking alembic programmatically.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#connection-sharing

    When calling alembic from the CLI,we need to create a new connection
    """

    connection = config.attributes.get("connection", None)

    if connection is None:
        # only create Engine if we don't have a Connection
        # from the outside

        # If we don't have a connection, we can safely assume that Hyperion is not running
        # Migrations should have been called from the CLI. We thus want to point to the production database
        # As we want to use the production database, we can call the `get_settings` function directly
        # instead of using it as a dependency (`app.dependency_overrides.get(get_settings, get_settings)()`)
        settings = get_settings()
        connectable = get_db_engine(settings)

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()
    else:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    If a connection is already present in the context config, it means that we already are in an event loop.
    We can not create a second event loop in the same thread so we can not call `asyncio.run(run_async_migrations())`.
    Instead we need to call `run_async_migrations()` directly.
    This `connection` attributes should be set when invoking alembic programmatically.
    WARNING: SQLAlchemy does not support `Inspection on an AsyncConnection`. The call to Alembic must be wrapped in a `run_sync` call.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.

    If not connection were provided, we may assume we are not in an existing event loop (ie. alembic was invoking from the cli). We create a new event loop and run the migrations in it.
    """

    connectable = config.attributes.get("connection", None)

    if connectable is None:
        asyncio.run(run_async_migrations())
    else:
        do_run_migrations(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
