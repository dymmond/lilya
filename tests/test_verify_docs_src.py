"""Tests for docs_src verification script.

These tests verify the categorization and syntax-check logic of the verification script,
ensuring correct handling of different file patterns without executing full verification.
"""

from __future__ import annotations

from pathlib import Path

from scripts.verify_docs_src import categorize_file, check_syntax


class TestCategorization:
    """Test file categorization logic."""

    def test_relative_imports_categorized_as_skip(self, tmp_path: Path) -> None:
        """Files with relative imports should be categorized as skip-relative."""
        test_file = tmp_path / "relative_example.py"
        source = "from . import models\nfrom ..utils import helper"
        test_file.write_text(source)

        category = categorize_file(test_file, source)

        assert category == "skip-relative"

    def test_fictitious_modules_categorized_as_skip(self, tmp_path: Path) -> None:
        """Files importing fictitious modules should be categorized as skip-fictitious."""
        test_file = tmp_path / "fictitious_example.py"
        source = "from myapp.models import User\nfrom apps.handlers import get_user"
        test_file.write_text(source)

        category = categorize_file(test_file, source)

        assert category == "skip-fictitious"

    def test_lilya_app_instantiation_categorized_as_syntax_only(self, tmp_path: Path) -> None:
        """Files with app = Lilya( should be categorized as syntax-only."""
        test_file = tmp_path / "app_example.py"
        source = "from lilya.apps import Lilya\n\napp = Lilya(routes=[])"
        test_file.write_text(source)

        category = categorize_file(test_file, source)

        assert category == "syntax-only"


class TestSyntaxCheck:
    """Test syntax verification."""

    def test_valid_python_syntax_passes(self) -> None:
        """Valid Python code should pass syntax check."""
        source = """
def hello():
    return "world"

class MyClass:
    pass
"""

        passed, error = check_syntax(source)

        assert passed is True
        assert error is None

    def test_invalid_python_syntax_fails(self) -> None:
        """Invalid Python code should fail syntax check."""
        source = """
def broken(:
    return "this is broken"
"""

        passed, error = check_syntax(source)

        assert passed is False
        assert error is not None
        assert "SyntaxError" in error
