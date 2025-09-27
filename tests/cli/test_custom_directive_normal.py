import os
import shutil

import pytest

from tests.cli.utils import run_cmd


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


def generate(client):
    result = client.invoke(["createproject", "--with-structure", "myproject"])
    assert result.exit_code == 0

    os.chdir("myproject/myproject/apps")

    result = client.invoke(["createapp", "myapp"])
    assert result.exit_code == 0


def test_custom_directive(create_folders, client):
    os.environ["LILYA_DEFAULT_APP"] = "tests.cli.main:app"
    original_path = os.getcwd()

    generate(client)

    # Back to starting point
    os.chdir(original_path)

    # Copy the createsuperuser custom directive
    shutil.copyfile(
        "normal_directive.py",
        "myproject/myproject/apps/myapp/directives/operations/normal_directive.py",
    )

    # Execute custom directive
    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya run --directive normal_directive")

    assert "Working" in str(o)
