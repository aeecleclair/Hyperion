import importlib
import logging
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from pytest_alembic import MigrationContext
from pytest_alembic.config import Config
from pytest_alembic.tests import (
    test_model_definitions_match_ddl,  # noqa: F401
    test_single_head_revision,  # noqa: F401
    test_up_down_consistency,  # noqa: F401
    test_upgrade,  # noqa: F401
)
from pytest_alembic.tests.experimental import downgrade_leaves_no_trace  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_migration.db"


pre_test_upgrade_dict: dict[
    str,
    Callable[[MigrationContext, Connection], None],
] = {}
test_upgrade_dict: dict[
    str,
    Callable[[MigrationContext, Connection], None],
] = {}

logger = logging.getLogger("hyperion_tests")


class FailedToRunPreTestUpgrade(Exception):
    pass


class FailedToRunUpgrade(Exception):
    pass


class FailedToRunTestUpgrade(Exception):
    pass


class MissingMigrationTestOrPretest(Exception):
    pass


def run_pre_test_upgrade(
    revision: str,
    alembic_runner: "MigrationContext",
    alembic_engine: Connection,
) -> None:
    if revision in pre_test_upgrade_dict:
        pre_test_upgrade_dict[revision](alembic_runner, alembic_engine)


def run_test_upgrade(
    revision: str,
    alembic_runner: "MigrationContext",
    alembic_engine: Connection,
) -> None:
    if revision in test_upgrade_dict:
        test_upgrade_dict[revision](alembic_runner, alembic_engine)


def have_revision_pretest_and_test(revision: str) -> bool:
    return revision in test_upgrade_dict and revision in pre_test_upgrade_dict


@pytest.fixture()
def alembic_config() -> Config:
    """Override this fixture to configure the exact alembic context setup required."""
    return Config()


@pytest.fixture()
def alembic_engine(alembic_connection) -> Connection:
    """
    Override this fixture to provide pytest-alembic powered tests with a database handle.

    The fixture yields a SQLAlchemy connection object. This fixture should be run before each tests, to ensure that the database is empty.

    Due to an issue with event loop, we can't run Alembic from asynchronous functions. The tests can't be async, so we need to use a synchronous connection.

    NOTE: the fixture is named `alembic_engine` but it should return a connection object.
    """
    return alembic_connection


@pytest.fixture()
def alembic_connection() -> Generator[Connection, None, None]:
    """
    The fixture yields a SQLAlchemy connection object. This fixture should be run before each tests, to ensure that the database is empty.

    Due to an issue with event loop, we can't run Alembic from asynchronous functions. The tests can't be async, so we need to use a synchronous connection.
    """
    # We need to delete the test database before each test
    Path("test_migration.db").unlink(missing_ok=True)

    # We use `echo=False` to disable SQLAlchemy logging for migrations
    # as errors are easier to see without all SQLAlchemy info
    connectable = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)

    with connectable.begin() as connection:
        yield connection

    connectable.dispose()


@pytest.fixture(scope="module")
def init_migration_scripts() -> None:  # noqa: PT004
    """
    We import all migration scripts in the migration/versions directory to extract the pre_test_upgrade and test_upgrade functions.
    """
    global pre_test_upgrade_dict, test_upgrade_dict

    for migration_file_path in Path().glob("migrations/versions/*.py"):
        if migration_file_path.stem == "__init__":
            continue
        migration_file = importlib.import_module(
            ".".join(migration_file_path.with_suffix("").parts),
        )
        if hasattr(migration_file, "revision"):
            revision = migration_file.revision
            if hasattr(migration_file, "pre_test_upgrade"):
                pre_test_upgrade = migration_file.pre_test_upgrade
                pre_test_upgrade_dict[revision] = pre_test_upgrade
            if hasattr(migration_file, "test_upgrade"):
                test_upgrade = migration_file.test_upgrade
                test_upgrade_dict[revision] = test_upgrade


def test_all_migrations_have_tests(
    alembic_runner: MigrationContext,
    init_migration_scripts: None,
) -> None:
    """
    Make sure that all migrations have a pretest and a test.
    """
    for revision in alembic_runner.history.revisions:
        if revision in ["base", "heads"]:
            continue
        if not have_revision_pretest_and_test(revision):
            raise MissingMigrationTestOrPretest(
                f"Revision {revision} doesn't have a pretest or a test",
            )


def test_migrations(
    alembic_runner: MigrationContext,
    alembic_connection: Connection,
    init_migration_scripts: None,
) -> None:
    for revision in alembic_runner.history.revisions:
        logger.info(f"Running tests for revision {logger}")
        try:
            run_pre_test_upgrade(revision, alembic_runner, alembic_connection)
        except Exception as error:
            raise FailedToRunPreTestUpgrade(f"Revision {revision}") from error
        try:
            alembic_runner.managed_upgrade(revision)
        except Exception as error:
            raise FailedToRunUpgrade(f"Revision {revision}") from error
        try:
            run_test_upgrade(revision, alembic_runner, alembic_connection)
        except Exception as error:
            raise FailedToRunTestUpgrade(f"Revision {revision}") from error
