from typing import Any

from dataclasses import dataclass

from lilya.encoders import apply_structure, json_encode

@dataclass
class Foo:
    a: int
    b: int

simplified = json_encode(Foo(a=3, b=5))
# dict {"a": 3, "b": 5}
foo = apply_structure(Foo, simplified)
# now a Foo object again
assert foo == Foo(a=3, b=5)
