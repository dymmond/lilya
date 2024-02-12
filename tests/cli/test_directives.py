import os
import shutil

import pytest
from tests.cli.utils import run_cmd

from lilya.app import Lilya

app = Lilya(routes=[])


FOUND_DIRECTIVES = ["createdeployment", "createapp", "createproject", "runserver", "show_urls"]


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


def test_list_directives_no_app(create_folders):
    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya directives", is_app=False)
    assert ss == 0

    for directive in FOUND_DIRECTIVES:
        assert directive in str(o)


def test_list_directives_with_app(create_folders):
    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya directives")
    assert ss == 0

    for directive in FOUND_DIRECTIVES:
        assert directive in str(o)


def test_list_directives_with_flag(create_folders):
    original_path = os.getcwd()
    run_cmd("tests.cli.main:app", "lilya createproject myproject --with-structure")

    os.chdir("myproject/myproject/apps")

    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya createapp myapp")

    os.chdir(original_path)

    shutil.copyfile(
        "createsuperuser.py",
        "myproject/myproject/apps/myapp/directives/operations/createsuperuser.py",
    )

    (o, e, ss) = run_cmd("tests.cli.main:app", "lilya --app tests.cli.main:app directives")
    assert ss == 0

    for directive in FOUND_DIRECTIVES:
        assert directive in str(o)

    assert "createsuperuser" in str(o)