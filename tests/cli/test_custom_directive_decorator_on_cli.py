import os
import shutil
from pathlib import Path

from sayer.testing import SayerTestClient

from tests.cli.utils import force_discovery_and_get_app, generate_project, pushd, resolve_fixture


def test_custom_directive_display(tmp_path, client):
    os.environ["LILYA_DEFAULT_APP"] = "tests.cli.main:app"

    project_root = generate_project(client, base_dir=tmp_path)  # /tmp/.../myproject
    ops_dir = project_root / "myproject" / "apps" / "myapp" / "directives" / "operations"
    ops_dir.mkdir(parents=True, exist_ok=True)

    here = Path(__file__).resolve()
    src_directive = resolve_fixture("createusercli.py", here)
    shutil.copyfile(src_directive, ops_dir / "createusercli.py")

    app = force_discovery_and_get_app(
        project_root=project_root,
        directive_pkg="myproject.apps.myapp.directives.operations.createusercli",
        app_mod="tests.cli.main",
        app_attr="app",
    )

    runner = SayerTestClient(app.cli)
    with pushd(project_root):
        result = runner.invoke(["--help"])

    assert result.exit_code == 0
    assert "create-user" in result.output


def test_custom_directive_run(tmp_path, client):
    os.environ["LILYA_DEFAULT_APP"] = "tests.cli.main:app"

    project_root = generate_project(client, base_dir=tmp_path)
    ops_dir = project_root / "myproject" / "apps" / "myapp" / "directives" / "operations"
    ops_dir.mkdir(parents=True, exist_ok=True)

    here = Path(__file__).resolve()
    src_directive = resolve_fixture("createusercli.py", here)
    shutil.copyfile(src_directive, ops_dir / "createusercli.py")

    app = force_discovery_and_get_app(
        project_root=project_root,
        directive_pkg="myproject.apps.myapp.directives.operations.createusercli",
        app_mod="tests.cli.main",
        app_attr="app",
    )

    runner = SayerTestClient(app.cli)
    with pushd(project_root):
        result = runner.invoke(["create-user", "--name", "lilya"])

    assert result.exit_code == 0
    assert "Superuser lilya created successfully." in result.output
