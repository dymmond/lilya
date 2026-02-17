#!/usr/bin/env python3
"""
Circular Import Detection Utility for Lilya

Detects circular import dependencies in the lilya package using static AST analysis.
Distinguishes between runtime imports and TYPE_CHECKING-only imports.

Exit codes:
    0: No runtime circular imports found
    1: Runtime circular imports detected
    2: Script execution error
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that extracts import statements and tracks TYPE_CHECKING scoping."""

    def __init__(self, module_path: str):
        self.module_path = module_path
        self.runtime_imports: list[str] = []
        self.type_checking_imports: list[str] = []
        self._in_type_checking = False
        self._type_checking_depth = 0

    def visit_If(self, node: ast.If) -> None:
        """Track TYPE_CHECKING blocks."""
        # Check if this is `if TYPE_CHECKING:`
        is_type_checking = False
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            is_type_checking = True
        elif isinstance(node.test, ast.Attribute):
            # Handle `if typing.TYPE_CHECKING:`
            if (
                isinstance(node.test.value, ast.Name)
                and node.test.value.id == "typing"
                and node.test.attr == "TYPE_CHECKING"
            ):
                is_type_checking = True

        if is_type_checking:
            old_in_type_checking = self._in_type_checking
            old_depth = self._type_checking_depth
            self._in_type_checking = True
            self._type_checking_depth += 1

            # Visit children within TYPE_CHECKING block
            for child in node.body:
                self.visit(child)

            self._in_type_checking = old_in_type_checking
            self._type_checking_depth = old_depth
        else:
            # Regular if statement
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Handle `import module` statements."""
        for alias in node.names:
            module_name = alias.name
            if module_name.startswith("lilya"):
                target = (
                    self.type_checking_imports if self._in_type_checking else self.runtime_imports
                )
                target.append(module_name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle `from module import ...` statements."""
        if node.module and node.module.startswith("lilya"):
            target = self.type_checking_imports if self._in_type_checking else self.runtime_imports
            target.append(node.module)


def module_path_to_name(file_path: Path, base_path: Path) -> str:
    """Convert file path to Python module name."""
    relative = file_path.relative_to(base_path)
    parts = list(relative.parts)

    # Remove .py extension
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    # Remove __init__ from module names
    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts) if parts else ""


def normalize_module(from_module: str, import_module: str) -> str:
    """
    Normalize relative imports to absolute module names.

    Args:
        from_module: The module doing the importing (e.g., 'lilya.apps')
        import_module: The imported module (e.g., 'lilya.routing' or relative)

    Returns:
        Absolute module name
    """
    # Already absolute
    if import_module.startswith("lilya."):
        return import_module

    # Relative import (would need special handling, but Lilya uses absolute imports)
    return import_module


def parse_imports(file_path: Path, base_path: Path) -> tuple[str, list[str], list[str]]:
    """
    Parse imports from a Python file.

    Returns:
        Tuple of (module_name, runtime_imports, type_checking_imports)
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        module_name = module_path_to_name(file_path, base_path)
        visitor = ImportVisitor(module_name)
        visitor.visit(tree)

        return module_name, visitor.runtime_imports, visitor.type_checking_imports
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}", file=sys.stderr)
        return "", [], []
    except Exception as e:
        print(f"⚠️  Error parsing {file_path}: {e}", file=sys.stderr)
        return "", [], []


def build_dependency_graph(
    lilya_path: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """
    Build dependency graphs for runtime and TYPE_CHECKING imports.

    Returns:
        Tuple of (runtime_graph, type_checking_graph)
        Each graph maps module -> set of modules it imports
    """
    runtime_graph: dict[str, set[str]] = defaultdict(set)
    type_checking_graph: dict[str, set[str]] = defaultdict(set)

    python_files = list(lilya_path.rglob("*.py"))
    print(f"📁 Scanning {len(python_files)} Python files in {lilya_path.name}/\n")

    for py_file in python_files:
        module_name, runtime_imports, type_checking_imports = parse_imports(
            py_file, lilya_path.parent
        )

        if not module_name:
            continue

        # Group imports to top-level module (e.g., lilya._internal._helpers -> lilya._internal)
        for imp in runtime_imports:
            # Normalize to module group level for cycle detection
            target_module = extract_module_group(imp)
            source_module = extract_module_group(module_name)

            # Only track cross-module dependencies
            if target_module != source_module:
                runtime_graph[source_module].add(target_module)

        for imp in type_checking_imports:
            target_module = extract_module_group(imp)
            source_module = extract_module_group(module_name)

            if target_module != source_module:
                type_checking_graph[source_module].add(target_module)

    return runtime_graph, type_checking_graph


def extract_module_group(module_name: str) -> str:
    """
    Extract module group from full module path.

    Examples:
        'lilya.apps' -> 'lilya.apps'
        'lilya._internal._helpers' -> 'lilya._internal'
        'lilya.middleware.cors' -> 'lilya.middleware'
        'lilya.conf.global_settings' -> 'lilya.conf'
    """
    if not module_name.startswith("lilya."):
        return module_name

    parts = module_name.split(".")

    # Single-file modules at top level
    if len(parts) == 2 and parts[1] in (
        "apps",
        "routing",
        "responses",
        "dependencies",
        "requests",
        "datastructures",
        "encoders",
        "transformers",
        "controllers",
        "environments",
        "context",
        "permissions",
    ):
        return module_name

    # Package modules (take first two parts: lilya.<package>)
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"

    return module_name


def detect_cycles_dfs(graph: dict[str, set[str]]) -> tuple[list[list[str]], list[list[str]]]:
    """
    Detect cycles in dependency graph using DFS.

    Returns:
        Tuple of (simple_cycles, complex_cycles)
        - simple_cycles: 2-3 node cycles (direct coupling, most actionable)
        - complex_cycles: 4+ node cycles (transitive dependencies)
    """
    all_cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str) -> bool:
        """DFS helper that returns True if cycle detected."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Cycle detected - extract the cycle from path
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                all_cycles.append(cycle)
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node)

    # Separate simple (2-3 nodes) from complex (4+) cycles
    simple_cycles = [
        c for c in all_cycles if len(c) <= 4
    ]  # 2-3 unique nodes (cycle has duplicate at end)
    complex_cycles = [c for c in all_cycles if len(c) > 4]

    return simple_cycles, complex_cycles


def format_cycle(cycle: list[str]) -> str:
    """Format a cycle for display."""
    return " → ".join(cycle)


def main() -> int:
    """Main entry point."""
    # Find lilya package directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    lilya_path = repo_root / "lilya"

    if not lilya_path.exists():
        print(f"❌ Error: lilya package not found at {lilya_path}", file=sys.stderr)
        return 2

    print("🔍 Lilya Circular Import Detector\n")
    print("=" * 70)

    # Build dependency graphs
    runtime_graph, type_checking_graph = build_dependency_graph(lilya_path)

    print("📊 Built dependency graph:")
    print(f"   • {len(runtime_graph)} modules with runtime imports")
    print(f"   • {len(type_checking_graph)} modules with TYPE_CHECKING imports")
    print()

    runtime_simple, runtime_complex = detect_cycles_dfs(runtime_graph)
    type_checking_simple, type_checking_complex = detect_cycles_dfs(type_checking_graph)

    print("=" * 70)
    print("\n🔄 CIRCULAR DEPENDENCY ANALYSIS\n")

    total_runtime = len(runtime_simple) + len(runtime_complex)
    total_type_checking = len(type_checking_simple) + len(type_checking_complex)

    if runtime_simple:
        print(f"⚠️  DIRECT RUNTIME CIRCULAR IMPORTS: {len(runtime_simple)} found")
        print("   Severity: HIGH (2-3 node cycles, direct coupling)\n")
        for i, cycle in enumerate(runtime_simple, 1):
            print(f"   {i}. {format_cycle(cycle)}")
        print()

    if runtime_complex:
        print(f"ℹ️  TRANSITIVE RUNTIME CIRCULAR IMPORTS: {len(runtime_complex)} found")
        print("   Severity: MEDIUM (4+ node cycles, indirect coupling)\n")
        for i, cycle in enumerate(runtime_complex, 1):
            print(f"   {i}. {format_cycle(cycle)}")
        print()

    if not total_runtime:
        print("✅ No runtime circular imports detected")
        print()

    if type_checking_simple:
        print(f"ℹ️  DIRECT TYPE_CHECKING circular imports: {len(type_checking_simple)} found")
        print("   Severity: LOW (type-checking only, no runtime risk)\n")
        for i, cycle in enumerate(type_checking_simple, 1):
            print(f"   {i}. {format_cycle(cycle)}")
        print()

    if type_checking_complex:
        print(f"ℹ️  TRANSITIVE TYPE_CHECKING circular imports: {len(type_checking_complex)} found")
        print("   Severity: LOW (type-checking only, no runtime risk)\n")
        for i, cycle in enumerate(type_checking_complex, 1):
            print(f"   {i}. {format_cycle(cycle)}")
        print()

    if not total_type_checking:
        print("✅ No TYPE_CHECKING circular imports detected")
        print()

    print("=" * 70)
    print("\n📋 SUMMARY\n")
    print(f"   • Scanned: {lilya_path.name}/ directory")
    print(f"   • Direct runtime cycles (2-3 nodes): {len(runtime_simple)}")
    print(f"   • Transitive runtime cycles (4+ nodes): {len(runtime_complex)}")
    print(f"   • TYPE_CHECKING cycles: {total_type_checking}")
    print()

    if runtime_simple:
        print("❌ FAIL: Direct runtime circular imports detected")
        print("   These pose immediate import-time execution risks and should be resolved.")
        print(f"   Focus on the {len(runtime_simple)} direct cycles first.")
        return 1
    elif runtime_complex:
        print("⚠️  WARNING: Transitive runtime circular imports detected")
        print("   These are lower priority but indicate tight coupling.")
        print("   Consider refactoring to reduce dependency complexity.")
        return 0
    else:
        print("✅ PASS: No runtime circular imports")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(2)
