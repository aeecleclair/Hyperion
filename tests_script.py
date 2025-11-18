#!/usr/bin/env python3
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging for GitHub Actions
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# We ignore .md files and GitHub workflows and app/modules to detect the scope of the changes
IGNORE_PATHS_START = ("app/modules/", "tests/modules/", ".github/")
IGNORE_EXTENSIONS = (".md",)


def get_changed_files():
    """Enumerate files changed compared to main branch."""
    try:
        diff = subprocess.check_output(  # noqa: S603
            ["git", "diff", "--name-only", "origin/main..."],  # noqa: S607
            text=True,
        ).strip()
        return diff.splitlines()
    except subprocess.CalledProcessError:
        return []


def detect_modules(changed_files):
    """Detect impacted modules based on file paths."""
    modules = set()
    for f in changed_files:
        logger.info(f"Changed file: {f}")
        # We want to detect changes in app/modules/<module_name>/...
        if f.startswith("app/modules/"):
            module = f.split("/")[2]
            modules.add(module)
        # Or the modification of tests in tests/modules/<module_name>/... or tests/modules/test_<module_name>*.py
        elif f.startswith("tests/modules/"):
            parts = f.split("/")
            if parts[2].startswith("test_"):
                module = parts[2][5:].split(".")[0].split("_")[0]
            else:
                module = parts[2]
            modules.add(module)
    return sorted(modules)


def is_module_scope_only(changed_files):
    """Check if the changes are only within module scopes."""
    return all(
        f.startswith(IGNORE_PATHS_START) or f.endswith(IGNORE_EXTENSIONS)
        for f in changed_files
    )


def get_modules_tests_patterns(modules):
    """Run pytest with coverage on core + modified modules."""
    patterns = []
    for mod in modules:
        # Check for tests/modules/test_mod*.py pattern
        path1 = f"tests/modules/test_{mod}*.py"
        # Check for tests/modules/mod/ directory pattern
        path2 = f"tests/modules/{mod}/"

        found_tests = False

        # Check if direct test files exist
        if list(Path().glob(path1)):
            patterns.append(path1)
            found_tests = True

        # Check if module directory with tests exists
        if Path(path2).exists() and Path(path2).is_dir():
            patterns.append(path2)
            found_tests = True

        if not found_tests:
            logger.warning(f"No tests found for module: {mod}")

    return patterns


def get_other_tests_patterns(changed_files: list[str]) -> list[str]:
    """Get patterns for other tests based on changed files."""
    patterns = []
    # If a database model changed, run migrations
    if any("models" in f for f in changed_files):
        patterns.append("tests/test_migrations.py")
    # If a factory changed, run factories tests
    if any("factory" in f for f in changed_files):
        patterns.append("tests/test_factories.py")
    return patterns


def run_tests(modules, changed_files, coverage=True, run_all=False):
    """Run tests based on changed modules."""
    base_cmd = [
        "pytest",
    ]
    if coverage:
        base_cmd += [
            "--cov",
        ]

    if run_all:
        logger.info("Running all tests.")
        base_cmd += ["tests/"]
        return sys.exit(subprocess.call(base_cmd))  # noqa: S603

    module_patterns = get_modules_tests_patterns(modules)
    if not module_patterns:
        logger.warning("No tests found for the changed modules.")
    else:
        logger.info(f"Impacted modules tests: {', '.join(module_patterns)}")
        base_cmd += module_patterns

    other_tests = get_other_tests_patterns(changed_files)
    if other_tests:
        logger.info(f"Additional tests to run: {', '.join(other_tests)}")
        base_cmd += other_tests

    logger.info(f"Running tests with command: {' '.join(base_cmd)}")
    sys.exit(subprocess.call(base_cmd))  # noqa: S603


if __name__ == "__main__":
    # Detect arg --cov and --all
    coverage = "--cov" in sys.argv
    run_all = "--all" in sys.argv

    changed_files = get_changed_files()
    # First detect if the --all flag is set or if there are no changed files outside module scope
    scope_only = not run_all and is_module_scope_only(changed_files)

    # First we check if changes are module-scoped only
    # If so, we run tests only for those modules
    if scope_only:
        logger.info("Changes are module-scoped only.")
        modules = detect_modules(changed_files)
        run_tests(modules, changed_files, coverage=coverage)
    # Else
    else:
        logger.info("Changes affect broader scope, running all tests.")
        modules = []
        run_tests(modules, changed_files, coverage=coverage, run_all=True)
