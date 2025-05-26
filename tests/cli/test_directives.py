import os
import shutil

import pytest

from lilya.apps import Lilya
from tests.cli.utils import run_cmd

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
