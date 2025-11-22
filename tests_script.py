import logging
import re
import subprocess
import sys
from pathlib import Path

# Configure logging for GitHub Actions
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# We ignore .md files and GitHub workflows and app/modules to detect the scope of the changes
IGNORE_PATHS_START = ("app/modules/", "tests/modules/", "migrations/", ".github/", ".vscode/")
IGNORE_EXTENSIONS = (".md",)


def get_changed_files():
    """Enumerate files changed compared to main branch."""
    # We use git diff to get the list of changed files with three dots (...) to compare with the base commit of the PR in the main branch
    diff = subprocess.check_output(  # noqa: S603
        ["git", "diff", "--name-only", "origin/main..."],  # noqa: S607
        text=True,
    ).strip()
    return diff.splitlines()


def detect_modules(changed_files):
    """Detect impacted modules based on file paths."""
    modules = set()

    # Regex patterns for module detection
    app_module_pattern = re.compile(r"^app/modules/([^/]+)/")
    test_module_pattern = re.compile(r"^tests/modules/(?:test_)?([^/.]+)")

    for f in changed_files:
        logger.info(f"Changed file: {f}")

        # Check for app/modules/<module_name>/...
        app_match = app_module_pattern.match(f)
        if app_match:
            modules.add(app_match.group(1))
            continue

        # Check for tests/modules/<module_name>/... or tests/modules/test_<module_name>*.py
        test_match = test_module_pattern.match(f)
        if test_match:
            modules.add(test_match.group(1))

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
        # Check for tests/modules/test_mod.py pattern
        path1 = f"tests/modules/test_{mod}.py"
        # Check for tests/modules/mod/ directory pattern
        path2 = f"tests/modules/{mod}/"

        found_tests = False

        # Check if direct test files exist
        if any(Path().glob(path1)):
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
    if any("models" in f or "migrations/" in f for f in changed_files):
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

    intial_cmd_length = len(base_cmd)

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

    # Do not run if no tests have been added to the base_cmd
    if len(base_cmd) == intial_cmd_length:
        logger.info("No tests to run.")
        return None

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
