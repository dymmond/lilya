import os
import shutil

import pytest

from lilya.conf import settings
from tests.cli.utils import run_cmd

models = settings.registry
pytestmark = pytest.mark.anyio


@pytest.fixture(scope="module")
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


def generate():
    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya createproject myproject --with-structure")
    assert ss == 0

    os.chdir("myproject/myproject/apps")

    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya createapp myapp")


async def test_custom_directive(create_folders):
    original_path = os.getcwd()

    generate()

    # Back to starting point
    os.chdir(original_path)

    # Copy the createuser custom directive
    shutil.copyfile(
        "createusercli.py",
        "myproject/myproject/apps/myapp/directives/operations/createusercli.py",
    )

    # Execute custom directive
    name = "Lilya"
    (o, e, ss) = run_cmd("tests.cli.main:app", f"lilya create-user -n {name}")
