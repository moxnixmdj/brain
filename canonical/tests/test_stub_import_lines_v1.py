"""`stub_imports` must receive the raw import LINES, not the parsed identifiers.

This one bug cost item 180 through five separate "fixes" to the head ranking. `solve_item` passed
`stub_names` (identifiers with the `import` keyword stripped) into a parameter whose whole job is
to decide which names are MODULES. With no `import sympy` line to read, the module root `sympy`
was indistinguishable from a bound callable, so every ranking decision built on it was wrong -- and
the wrongness MOVED each time the ranking changed, which is why it read as a ranking problem.

The observable asserted here is the one that actually differs: which head the lambda space is
built on. Ranked on identifiers, the space is dominated by `Max(expr).replace(...)`; ranked on
lines it is dominated by `parse_mathematica(expr).replace(...)`.
"""
from __future__ import annotations

import collections
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import body_grammar_v1 as G

STUB = ("from sympy.parsing.mathematica import parse_mathematica\n"
        "from sympy import Function, Max, Min\n"
        "import sympy\n\n"
        "def f(expr : str) -> int:\n    return ")

PROBLEM = ("every occurrence of the function symbol F is replaced by a new function that "
           "returns the product of the maximum and the minimum of those arguments")

KW = dict(
    problem=PROBLEM,
    stated_symbols=["sympy.parsing.mathematica.parse_mathematica", "sympy.Max", "sympy.Min"],
    return_annotations=["int"],
    imported_names=["parse_mathematica", "Function", "Max", "Min", "sympy", "str"],
)
LINES = [ln for ln in STUB.splitlines() if ln.strip().startswith(("import ", "from "))]
HIT = "parse_mathematica(expr).replace(Function('F'), lambda *x: Min(*x)*Max(*x))"


def _heads(space):
    return collections.Counter(b["body"].split(".replace(", 1)[0]
                               for b in space if ".replace(" in b["body"])


def test_the_stub_lines_are_readable_as_lines():
    assert LINES == ["from sympy.parsing.mathematica import parse_mathematica",
                     "from sympy import Function, Max, Min",
                     "import sympy"]


def test_the_stated_body_is_the_FIRST_thing_the_space_offers():
    """What actually matters is not that no constructor is ever a head -- Max(expr).replace()
    is a legal string, just an obviously wrong answer -- but that the stated body comes FIRST,
    so no cap can ever hide it. Measured: index 6 of 129."""
    bodies = [b["body"] for b in G.compositions(["expr"], {}, stub_imports=LINES, **KW)]
    assert HIT in bodies
    assert bodies.index(HIT) < 10, bodies.index(HIT)


def test_the_stub_import_lines_parameter_accepts_two_shapes_without_crashing():
    """I claimed the lines-vs-identifiers distinction was the cause of the 180 regression. It
    was NOT: measured, both shapes produce the same space. The comment is kept as a record of a
    wrong hypothesis rather than deleted, and this test pins only what is true -- the parameter
    tolerates both and the stated body is present either way."""
    for shape in (LINES, ["parse_mathematica", "Max", "Min", "sympy"]):
        bodies = [b["body"] for b in G.compositions(["expr"], {}, stub_imports=shape, **KW)]
        assert HIT in bodies


def test_the_stated_body_is_reachable_in_the_space():
    bodies = [b["body"] for b in G.compositions(["expr"], {}, stub_imports=LINES, **KW)]
    assert HIT in bodies
