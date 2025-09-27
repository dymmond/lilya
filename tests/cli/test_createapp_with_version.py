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


def _run_asserts():
    assert os.path.isfile("myapp/__init__.py") is True
    assert os.path.isfile("myapp/tests.py") is True
    assert os.path.isfile("myapp/v10/__init__.py") is True
    assert os.path.isfile("myapp/v10/schemas.py") is True
    assert os.path.isfile("myapp/v10/urls.py") is True
    assert os.path.isfile("myapp/v10/controllers.py") is True
    assert os.path.isfile("myapp/directives/__init__.py") is True
    assert os.path.isfile("myapp/directives/operations/__init__.py") is True


def test_create_app_with_env_var(create_folders, client):
    os.environ["LILYA_DEFAULT_APP"] = "tests.cli.main:app"

    result = client.invoke(["createproject", "--with-structure", "myproject"])
    assert result.exit_code == 0

    os.chdir("myproject/myproject/apps")

    result = client.invoke(["createapp", "myapp", "--version", "v10"])

    _run_asserts()


def test_create_app_without_env_var(create_folders, client):
    result = client.invoke(["createproject", "--with-structure", "myproject"])
    assert result.exit_code == 0

    os.chdir("myproject/myproject/apps")

    result = client.invoke(["createapp", "myapp", "--version", "v10"])
    assert result.exit_code == 0

    _run_asserts()
