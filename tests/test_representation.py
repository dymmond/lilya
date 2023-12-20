from dataclasses import dataclass

from lilya._internal._representation import Repr


class Dummy(Repr):
    def __init__(self, name=None, email=None):
        self.name = name
        self.email = email


@dataclass
class DummyDataclass:
    name: str = None
    email: str = None


def test_to_representation():
    dummy = Dummy()

    assert repr(dummy) == "Dummy()"

    dummy = Dummy(name="Lilya")

    assert repr(dummy) == "Dummy(name='Lilya')"

    dummy = Dummy(name="Lilya", email="lilya@lilya.dev")

    assert repr(dummy) == "Dummy(name='Lilya', email='lilya@lilya.dev')"


def test_to_representation_dataclass():
    dummy = DummyDataclass()

    assert repr(dummy) == "DummyDataclass(name=None, email=None)"

    dummy = DummyDataclass(name="Lilya")

    assert repr(dummy) == "DummyDataclass(name='Lilya', email=None)"

    dummy = DummyDataclass(name="Lilya", email="lilya@lilya.dev")

    assert repr(dummy) == "DummyDataclass(name='Lilya', email='lilya@lilya.dev')"
