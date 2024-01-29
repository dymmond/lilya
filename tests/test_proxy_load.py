from lilya._internal._module_loading import ProxyLoad


class Dummy:
    def __init__(self, name=None, age=None) -> None:
        self.name = name
        self.age = age

    def get_name(self):
        return self.name


def test_proxy_load():
    dummy = ProxyLoad("tests.test_proxy_load.Dummy", name="test", age=1)

    assert str(dummy) == "<ProxyDummy()>"
