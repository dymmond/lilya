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
        shutil.rmtree("deployment")
    except OSError:
        pass
    try:
        shutil.rmtree("deploy")
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
        shutil.rmtree("deployment")
    except OSError:
        pass
    try:
        shutil.rmtree("deploy")
    except OSError:
        pass
    try:
        shutil.rmtree("temp_folder")
    except OSError:
        pass


def _run_asserts():
    assert os.path.isfile("deploy/docker/Dockerfile") is True
    assert os.path.isfile("deploy/gunicorn/gunicorn_conf.py") is True
    assert os.path.isfile("deploy/nginx/nginx.conf") is True
    assert os.path.isfile("deploy/nginx/nginx.json-logging.conf") is True
    assert os.path.isfile("deploy/supervisor/supervisord.conf") is True


def test_create_app_with_env_var(create_folders, client):
    os.environ["LILYA_DEFAULT_APP"] = "tests.cli.main:app"

    result = client.invoke(["createdeployment", "myproject", "--deployment-folder-name", "deploy"])
    assert result.exit_code == 0

    _run_asserts()


def test_create_app_without_env_var(create_folders, client):
    result = client.invoke(["createdeployment", "myproject", "--deployment-folder-name", "deploy"])
    assert result.exit_code == 0

    _run_asserts()


def test_create_app_without_env_var_with_app_flag(create_folders, client):
    result = client.invoke(
        [
            "--app",
            "tests.cli.main:app",
            "createdeployment",
            "myproject",
            "--deployment-folder-name",
            "deploy",
        ]
    )
    assert result.exit_code == 0

    _run_asserts()
