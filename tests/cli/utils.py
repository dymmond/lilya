import importlib
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


def run_cmd(app, cmd, is_app=True):
    if is_app:
        os.environ["LILYA_DEFAULT_APP"] = app

    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = process.communicate()
    print("\n$ " + cmd)
    print(stdout.decode("utf-8"))
    print(stderr.decode("utf-8"))
    return stdout, stderr, process.wait()


def _purge_modules(prefixes: tuple[str, ...]) -> None:
    for name in list(sys.modules):
        if any(name == p or name.startswith(p + ".") for p in prefixes):
            sys.modules.pop(name, None)


def force_discovery_and_get_app(
    project_root: str = "myproject",
    directive_pkg: str = "myproject.apps.myapp.directives.operations.createusercli",
    app_mod: str = "tests.cli.main",
    app_attr: str = "app",
):
    """
    Rebuild the CLI in-process so newly copied directives are discovered.

    Steps:
    - cd into project_root so lilya_cli uses the right Path.cwd()
    - invalidate caches & purge modules that cache CLI/registry
    - import the directive (registers its command)
    - re-import the app module and return a fresh app object
    """
    abs_root = os.path.abspath(project_root)
    os.chdir(abs_root)
    if abs_root not in sys.path:
        sys.path.insert(0, abs_root)

    importlib.invalidate_caches()

    _purge_modules(
        (
            "sayer.core.engine",  # resets COMMANDS/_GROUPS registries
            "lilya.cli",
            "lilya.cli.",  # ensures lilya_cli runs again (breakpoint triggers)
            "myproject.apps.myapp.directives",  # directive pkg subtree
            app_mod,  # your app module (tests.cli.main)
        )
    )

    importlib.invalidate_caches()
    importlib.import_module("sayer.core.engine")
    importlib.import_module(directive_pkg)

    module = importlib.import_module(app_mod)

    app = getattr(module, app_attr)
    return app


def resolve_fixture(file_name: str, anchor_file: Path) -> Path:
    """
    Locate a fixture file (e.g., 'createusercli.py') relative to the test file,
    independent of current working directory.
    """
    anchor_dir = anchor_file.parent.resolve()
    candidate = anchor_dir / file_name
    if candidate.is_file():
        return candidate

    shared = anchor_dir / file_name
    if shared.is_file():
        return shared
    raise FileNotFoundError(f"Fixture not found: {file_name!r} near {anchor_dir}")


@contextmanager
def pushd(path: str):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _ensure_pkg_tree(paths) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
        init = p / "__init__.py"
        init.touch(exist_ok=True)


def generate_project(client, base_dir: Path) -> Path:
    """
    Create 'myproject' under 'base_dir' and return the absolute project root path:
      base_dir / "myproject"

    This uses the same CLI you know works (subprocess), and runs 'createapp'
    from the *apps_dir* so the app lands in the right place.
    """
    base_dir = Path(base_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    prev = Path.cwd()
    try:
        os.chdir(base_dir)
        result = client.invoke(["createproject", "myproject", "--with-structure"])
        assert result.exit_code == 0
    finally:
        os.chdir(prev)

    project_root = base_dir / "myproject"
    pkg_root = project_root / "myproject"
    apps_dir = pkg_root / "apps"

    _ensure_pkg_tree([pkg_root, apps_dir])

    prev = Path.cwd()
    try:
        os.chdir(apps_dir)
        result = client.invoke(["createapp", "myapp"])
        ss = result.exit_code
        assert ss == 0
    finally:
        os.chdir(prev)

    assert apps_dir.is_dir(), f"apps dir not found at {apps_dir}"
    return project_root
