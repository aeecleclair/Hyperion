#!/usr/bin/env python3
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging for GitHub Actions
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


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
    """DDetect impacted modules based on file paths."""
    modules = set()
    for f in changed_files:
        logger.info(f"Changed file: {f}")
        if f.startswith("app/modules/"):
            module = f.split("/")[2]
            modules.add(module)
    return sorted(modules)


def is_module_scope_only(changed_files):
    """Check if the changes are only within module scopes."""
    # TODO: could be improved to ignore certain files like docs, etc.
    return all(f.startswith("app/modules/") for f in changed_files)


def run_tests(modules, coverage=True, run_all=False):
    """Run pytest with coverage on core + modified modules."""
    base_cmd = [
        "pytest",
    ]
    if coverage:
        base_cmd += [
            "--cov",
        ]

    if run_all:
        logger.info("Running all tests.")
        return sys.exit(subprocess.call(base_cmd))  # noqa: S603

    # core always tested
    patterns = ["tests/core/"]

    for mod in modules:
        path = f"tests/test_{mod}*.py"
        if Path(path).exists():
            patterns.append(path)

    if not modules:
        logger.info("No specific module modified, testing core only.")
    else:
        logger.info(f"Impacted modules: {', '.join(modules)}")

    logger.info(f"Launching tests: {patterns}")
    sys.exit(subprocess.call(base_cmd + patterns))  # noqa: S603


if __name__ == "__main__":
    changed = get_changed_files()
    modules = detect_modules(changed)
    scope_only = is_module_scope_only(changed)

    # Detect arg --cov
    coverage = "--cov" in sys.argv
    run_all = "--all" in sys.argv

    if scope_only and not run_all:
        logger.info("Changes are module-scoped only.")
        run_tests(modules, coverage=coverage)
    else:
        logger.info("Changes affect broader scope, running all tests.")
        run_tests(modules, coverage=coverage, run_all=True)
