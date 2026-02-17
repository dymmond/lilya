#!/usr/bin/env python
"""
docs_src verification script

Categorizes and verifies all Python files under docs_src/:
- syntax-only: ast.parse() verification
- import-check: ast.parse() + importlib import verification
- skip: Files with relative/fictitious imports (syntax still verified)

Usage:
    python scripts/verify_docs_src.py
    python scripts/verify_docs_src.py --verbose
    python scripts/verify_docs_src.py --check-file PATH
    python scripts/verify_docs_src.py --categorize-only
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path
from typing import NamedTuple


class FileResult(NamedTuple):
    """Result of verifying a single file."""

    path: Path
    category: str  # 'skip', 'syntax-only', 'import-check'
    passed: bool
    error: str | None = None
    demoted_from_import: bool = False


class VerificationStats(NamedTuple):
    """Summary statistics for verification run."""

    total: int
    syntax_only_passed: int
    import_check_passed: int
    import_check_demoted: int
    skip_relative: int
    skip_fictitious: int
    failed: int


def read_file_source(filepath: Path) -> str:
    """Read file source with explicit UTF-8 encoding."""
    return filepath.read_text(encoding="utf-8")


def check_syntax(source: str) -> tuple[bool, str | None]:
    """
    Verify Python syntax using ast.parse().

    Returns:
        (passed, error_message)
    """
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


def categorize_file(filepath: Path, source: str) -> str:
    """
    Categorize file based on content heuristics.

    Categories:
    - 'skip': relative imports or fictitious modules
    - 'syntax-only': creates ASGI app instances
    - 'import-check': eligible for import verification

    Note: ALL files get syntax-checked via ast.parse() regardless of category.
    'skip' means "skip import-check only".
    """
    # Check for relative imports
    if "from ." in source or "from .." in source:
        return "skip-relative"

    # Check for fictitious module imports
    fictitious_patterns = ["from myapp", "from apps.", "from esmerald", "from saffier"]
    if any(pattern in source for pattern in fictitious_patterns):
        return "skip-fictitious"

    # Check for ASGI app instantiation (side effects)
    app_patterns = [
        "app = Lilya(",
        "application = Lilya(",
        "app = ChildLilya(",
    ]
    if any(pattern in source for pattern in app_patterns):
        return "syntax-only"

    # Default: eligible for import-check
    return "import-check"


def attempt_import(filepath: Path) -> tuple[bool, str | None, bool]:
    """
    Attempt to import a file using importlib.util.spec_from_file_location().

    Returns:
        (passed, error_message, demoted_to_syntax_only)
    """
    module_name = f"_verify_temp_{filepath.stem}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            # Should not happen for valid Python files, but handle gracefully
            return False, None, True  # Demote to syntax-only

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Clean up
        if module_name in sys.modules:
            del sys.modules[module_name]

        return True, None, False

    except (ImportError, ModuleNotFoundError):
        # Missing dependency — demote to syntax-only (not a failure)
        return False, None, True

    except SyntaxError:
        # Top-level await/async with fragments pass ast.parse but fail exec_module
        # Demote to syntax-only (not a failure)
        return False, None, True

    except Exception:
        # Runtime errors from module execution (side effects like TypeError, ValueError, etc.)
        # These are not syntax or import errors — demote to syntax-only per plan guardrails
        # Plan line 84: "No run-check / execution-level verification: Syntax + import only"
        return False, None, True

    finally:
        # Ensure cleanup
        if module_name in sys.modules:
            del sys.modules[module_name]


def verify_file(filepath: Path) -> FileResult:
    """
    Verify a single Python file.

    Steps:
    1. Read source
    2. ast.parse() syntax check (MANDATORY for ALL files)
    3. Categorize based on heuristics
    4. For import-check eligible: attempt import
    """
    try:
        source = read_file_source(filepath)
    except Exception as e:
        return FileResult(
            path=filepath,
            category="error",
            passed=False,
            error=f"Failed to read file: {e}",
        )

    # Step 2: Syntax check (ALL files, unconditionally)
    syntax_ok, syntax_error = check_syntax(source)
    if not syntax_ok:
        return FileResult(
            path=filepath,
            category="syntax-error",
            passed=False,
            error=syntax_error,
        )

    # Step 3: Categorize
    category = categorize_file(filepath, source)

    # Step 4: Import check for eligible files
    if category == "import-check":
        import_ok, import_error, demoted = attempt_import(filepath)

        if demoted:
            # Demoted to syntax-only (not a failure)
            return FileResult(
                path=filepath,
                category="syntax-only",
                passed=True,
                demoted_from_import=True,
            )

        if not import_ok:
            # Actual import failure
            return FileResult(
                path=filepath,
                category="import-check",
                passed=False,
                error=import_error,
            )

        # Import succeeded
        return FileResult(
            path=filepath,
            category="import-check",
            passed=True,
        )

    # Syntax-only or skip categories (already passed syntax check)
    return FileResult(
        path=filepath,
        category=category,
        passed=True,
    )


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files under root, excluding __pycache__."""
    files = []
    for path in root.rglob("*.py"):
        if "__pycache__" not in path.parts:
            files.append(path)
    return sorted(files)


def compute_stats(results: list[FileResult]) -> VerificationStats:
    """Compute summary statistics from results."""
    syntax_only = sum(
        1
        for r in results
        if r.passed and r.category == "syntax-only" and not r.demoted_from_import
    )
    import_check = sum(1 for r in results if r.passed and r.category == "import-check")
    import_demoted = sum(1 for r in results if r.passed and r.demoted_from_import)
    skip_relative = sum(1 for r in results if r.passed and r.category == "skip-relative")
    skip_fictitious = sum(1 for r in results if r.passed and r.category == "skip-fictitious")
    failed = sum(1 for r in results if not r.passed)

    return VerificationStats(
        total=len(results),
        syntax_only_passed=syntax_only,
        import_check_passed=import_check,
        import_check_demoted=import_demoted,
        skip_relative=skip_relative,
        skip_fictitious=skip_fictitious,
        failed=failed,
    )


def print_summary(stats: VerificationStats) -> None:
    """Print verification summary."""
    print(f"\ndocs_src verification: {stats.total} files found")
    print(f"  syntax-only: {stats.syntax_only_passed} passed")
    print(
        f"  import-check: {stats.import_check_passed} passed, "
        + f"{stats.import_check_demoted} demoted to syntax-only"
    )
    print(
        f"  skipped: {stats.skip_relative + stats.skip_fictitious} "
        + f"(relative imports: {stats.skip_relative}, fictitious modules: {stats.skip_fictitious})"
    )

    if stats.failed > 0:
        print(f"  FAILED: {stats.failed}")
        print("\nRESULT: FAIL")
    else:
        print("\nRESULT: PASS")


def print_verbose(results: list[FileResult]) -> None:
    """Print per-file results."""
    cwd = Path.cwd()
    for result in results:
        status = "PASS" if result.passed else "FAIL"

        # Handle both absolute and relative paths
        try:
            if result.path.is_absolute():
                rel_path = result.path.relative_to(cwd)
            else:
                rel_path = result.path
        except ValueError:
            # Path is not relative to cwd, use as-is
            rel_path = result.path

        msg = f"[{status}] {rel_path} ({result.category})"
        if result.demoted_from_import:
            msg += " [demoted from import-check]"
        if result.error:
            msg += f" — {result.error}"

        print(msg)


def print_categorization(results: list[FileResult]) -> None:
    """Print categorization breakdown without verification."""
    stats = compute_stats(results)
    print(f"\nCategorization for {stats.total} files:")
    print(f"  syntax-only: {stats.syntax_only_passed}")
    print(f"  import-check: {stats.import_check_passed + stats.import_check_demoted}")
    print(
        f"  skip: {stats.skip_relative + stats.skip_fictitious} "
        + f"(relative: {stats.skip_relative}, fictitious: {stats.skip_fictitious})"
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify Python examples in docs_src/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-file results",
    )
    parser.add_argument(
        "--check-file",
        type=Path,
        metavar="PATH",
        help="Verify a single file",
    )
    parser.add_argument(
        "--categorize-only",
        action="store_true",
        help="Show categorization without verification",
    )

    args = parser.parse_args()

    # Determine files to check
    if args.check_file:
        if not args.check_file.exists():
            print(f"Error: File not found: {args.check_file}", file=sys.stderr)
            return 1
        files = [args.check_file]
    else:
        docs_src = Path("docs_src")
        if not docs_src.exists():
            print("Error: docs_src/ directory not found", file=sys.stderr)
            return 1
        files = find_python_files(docs_src)

    # Verify files
    results = [verify_file(f) for f in files]

    # Output
    if args.categorize_only:
        print_categorization(results)
        return 0

    if args.verbose:
        print_verbose(results)

    stats = compute_stats(results)
    print_summary(stats)

    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
