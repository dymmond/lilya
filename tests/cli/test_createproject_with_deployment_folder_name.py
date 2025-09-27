import os
import shutil

import pytest


@pytest.fixture(scope="function", autouse=True)
def create_folders():
    os.chdir(os.path.split(os.path.abspath(__file__))[0])
    try:
        os.remove("app.db")
    except OSError:
        pass
    try:
        shutil.rmtree("myproject")

    except OSError:
        pass
    try:
        shutil.rmtree("temp_folder")
    except OSError:
        pass

    yield

    os.chdir(os.path.split(os.path.abspath(__file__))[0])
    try:
        os.remove("app.db")
    except OSError:
        pass
    try:
        shutil.rmtree("myproject")

    except OSError:
        pass
    try:
        shutil.rmtree("temp_folder")
    except OSError:
        pass


def test_create_project(create_folders, client):
    result = client.invoke(
        [
            "createproject",
            "myproject",
            "--with-structure",
            "--with-deployment",
            "--deployment-folder-name",
            "deploy",
        ]
    )

    assert result.exit_code == 0

    with open("myproject/.gitignore") as f:
        assert f.readline().strip() == "# Byte-compiled / optimized / DLL files"
    with open("myproject/myproject/urls.py") as f:
        assert f.readline().strip() == '"""myproject Routes Configuration'


def _run_asserts():
    assert os.path.isfile("myproject/Taskfile.yaml") is True
    assert os.path.isfile("myproject/README.md") is True

    # Deployment
    assert os.path.isfile("myproject/deploy/docker/Dockerfile") is True
    assert os.path.isfile("myproject/deploy/gunicorn/gunicorn_conf.py") is True
    assert os.path.isfile("myproject/deploy/nginx/nginx.conf") is True
    assert os.path.isfile("myproject/deploy/nginx/nginx.json-logging.conf") is True
    assert os.path.isfile("myproject/deploy/supervisor/supervisord.conf") is True

    # General
    assert os.path.isfile("myproject/.gitignore") is True
    assert os.path.isfile("myproject/myproject/__init__.py") is True
    assert os.path.isfile("myproject/myproject/main.py") is True
    assert os.path.isfile("myproject/myproject/serve.py") is True
    assert os.path.isfile("myproject/myproject/urls.py") is True
    assert os.path.isfile("myproject/myproject/tests/__init__.py") is True
    assert os.path.isfile("myproject/myproject/tests/test_app.py") is True
    assert os.path.isfile("myproject/myproject/configs/__init__.py") is True
    assert os.path.isfile("myproject/myproject/configs/settings.py") is True
    assert os.path.isfile("myproject/myproject/configs/development/__init__.py") is True
    assert os.path.isfile("myproject/myproject/configs/development/settings.py") is True
    assert os.path.isfile("myproject/myproject/configs/testing/__init__.py") is True
    assert os.path.isfile("myproject/myproject/configs/testing/settings.py") is True
    assert os.path.isfile("myproject/myproject/apps/__init__.py") is True
    assert os.path.isfile("myproject/requirements/base.txt") is True
    assert os.path.isfile("myproject/requirements/testing.txt") is True
    assert os.path.isfile("myproject/requirements/development.txt") is True


def test_create_project_files_with_env_var(create_folders, client):
    os.environ["LILYA_DEFAULT_APP"] = "tests.cli.main:app"

    result = client.invoke(
        [
            "createproject",
            "myproject",
            "--with-structure",
            "--with-deployment",
            "--deployment-folder-name",
            "deploy",
        ]
    )

    assert result.exit_code == 0

    _run_asserts()


def test_create_project_files_without_env_var(create_folders, client):
    result = client.invoke(
        [
            "createproject",
            "myproject",
            "--with-structure",
            "--with-deployment",
            "--deployment-folder-name",
            "deploy",
        ]
    )
    assert result.exit_code == 0

    _run_asserts()


def test_create_project_files_without_env_var_and_with_app_flag(create_folders, client):
    result = client.invoke(
        [
            "--app",
            "tests.cli.main:app",
            "createproject",
            "myproject",
            "--with-structure",
            "--with-deployment",
            "--deployment-folder-name",
            "deploy",
        ]
    )
    assert result.exit_code == 0

    _run_asserts()
