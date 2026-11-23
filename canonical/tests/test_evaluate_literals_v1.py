"""Deciding a program's runtime faults from its own literals -- checked against REAL EXECUTION, not opinion.

§A116 measured that static reading found none of five runtime-state faults, and closed with the honest boundary:
the only thing that would help is observing behaviour without paying for the whole program. §A117's evidence is
that for the faults that actually break small programs, **every value involved is a literal in the source** --
no symbolic input, nothing to solve. So the mechanism is constant propagation, not a symbolic executor.

THE ASYMMETRY THAT GOVERNS THIS FILE. Two ways to be wrong, and they are not equally bad:

    a MISS    the walk says nothing and the program fails    -> one wasted execution of the run-and-look loop
    a FALSE ALARM  the walk reports a fault in a program that runs  -> the system "repairs" working code

The second destroys trust in the mechanism and changes code that was never broken, so every test below that
matters is a test about silence, and the faults found are checked by RUNNING the program rather than by asking
this module what it thinks.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import pytest

from canonical.runtime import evaluate_literals_v1 as E


def _actually_raises(source: str) -> bool:
    """Ground truth: run the program and see. The tests never take this module's word for it."""
    world = pathlib.Path(tempfile.mkdtemp(prefix="eval_"))
    (world / "p.py").write_text(source)
    return subprocess.run([sys.executable, "p.py"], cwd=world, capture_output=True, text=True).returncode != 0


#: Each program, chosen so that the value causing the fault is a literal the walk can follow.
CASES = [
    ("a=10\nb=0\nprint(a/b)", "zero_division"),
    ("a=10\nb=2\nprint(a/b)", None),
    ("a=10\nb=0\nprint(a%b)", "zero_division"),
    ("z=0\nprint(1//z)", "zero_division"),
    ("xs=[1,2]\nprint(xs[5])", "index_out_of_range"),
    ("xs=[1,2,3]\nprint(xs[2])", None),
    ("print([1,2][-3])", "index_out_of_range"),
    ('d={"a":1}\nprint(d["b"])', "key_not_found"),
    ('d={"a":1}\nprint(d["a"])', None),
    ("total=1\nfor n in [0,1]:\n    total=total/n\nprint(total)", "zero_division"),
    ("total=0\nfor n in [1,2,3]:\n    total=total/(n+1)\nprint(total)", None),
    ("x=1\nif x:\n    print(10/0)", "zero_division"),
    ("x=0\nif x:\n    print(10/0)\nelse:\n    print(1)", None),
    ("x = 5\nwhile x > 0:\n    x = x - 1\nprint(10/x)", "zero_division"),
    ("a,b=1,0\nprint(a/b)", "zero_division"),
]


@pytest.mark.parametrize("source,expected", CASES, ids=[c[0][:34] for c in CASES])
def test_the_verdict_matches_real_execution(source: str, expected: str | None) -> None:
    """Every verdict here is checked against the program actually running.

    A test that only compared the module to itself would prove it is consistent, not that it is right.
    """
    result = E.evaluate(source)
    found = [fault["class"] for fault in result["certain"]]
    actually = _actually_raises(source)
    assert actually == (expected is not None), "the fixture itself is wrong"
    if expected is None:
        assert found == [], result
    else:
        assert expected in found, result


def test_it_never_accuses_a_program_that_runs() -> None:
    """THE PROPERTY THAT MATTERS MOST, over the cases that produced the defects.

    Each of these was a FALSE ALARM at some point in this round, and each was found by trying to break the
    module rather than by reading it:
      * `xs.append(1)` -- an unmodelled mutating call left `xs` believed empty
      * `d["k"]=1`      -- subscript ASSIGNMENT was not applied, so `d` stayed `{}`
      * `try/except`    -- a caught fault was reported as fatal
      * `if b else 0`   -- a guarded division was reported unguarded
    """
    safe = [
        "xs=[]\nxs.append(1)\nprint(xs[0])",
        'd={}\nd["k"]=1\nprint(d["k"])',
        "a=10\nb=0\ntry:\n    print(a/b)\nexcept ZeroDivisionError:\n    print(0)",
        "a=10\nb=0\ntry:\n    print(a/b)\nexcept:\n    print(0)",
        "a=10\nb=0\nprint(a/b if b else 0)",
        "import sys\nn=int(sys.stdin.readline() or 1)\nprint(10/n)",
        'd={"a":1}\nprint(d.get("b"))',
        "x=[1,2,3]\nprint(x[1+1])",
        "a=10\nb=0\nc=a/b if False else 1\nprint(c)",
        "for i in range(0):\n    print(10/0)",
        "def f():\n    return 10/0\nprint(1)",
    ]
    for source in safe:
        assert _actually_raises(source) is False, "the fixture must actually run: %r" % source
        result = E.evaluate(source)
        assert result["certain"] == [], (source, result)


def test_a_fault_caught_by_its_own_handler_is_not_a_fault_but_a_mismatched_one_still_is() -> None:
    """The distinction that made the first guard wrong, in both directions.

    A guard that suppressed every fault inside a `try` reported `try/except KeyError` around a division as safe
    -- and that program CRASHES, because a KeyError handler does not catch a ZeroDivisionError.
    """
    caught = "a=10\nb=0\ntry:\n    print(a/b)\nexcept ZeroDivisionError:\n    print(0)"
    assert E.evaluate(caught)["certain"] == []

    mismatch = "a=10\nb=0\ntry:\n    print(a/b)\nexcept KeyError:\n    print(0)"
    assert _actually_raises(mismatch) is True
    assert [f["class"] for f in E.evaluate(mismatch)["certain"]] == ["zero_division"]


def test_an_unknown_is_reported_as_an_unknown_not_as_safety() -> None:
    """`NO_FAULT_FOUND` and `COULD_NOT_DECIDE` are different statements and must never be merged.

    A library call whose failure depends on mathematics is refused by name rather than modelled -- modelling it
    would need a table per library, which is the knowledge house in miniature. The important part is that the
    refusal is VISIBLE: a caller that reads only "no fault" would conclude the program is safe.
    """
    result = E.evaluate("import math\nprint(math.sqrt(-1))")
    assert result["certain"] == []
    assert result["verdict"] == "THIS_WALK_COULD_NOT_DECIDE"
    assert any("MATHEMATICAL_DOMAIN_NOT_MODELLED" in reason for reason in result["unknowns"])
    assert _actually_raises("import math\nprint(math.sqrt(-1))") is True

    clean = E.evaluate("print(1+1)")
    assert clean["certain"] == []
    assert clean["verdict"] == "NO_FAULT_FOUND_IN_WHAT_COULD_BE_FOLLOWED"


def test_it_refuses_a_program_it_cannot_parse() -> None:
    result = E.evaluate("def f(:\n")
    assert result["verdict"] == "CANNOT_READ"
    assert result["certain"] == []


def test_a_long_loop_is_refused_rather_than_unrolled_forever() -> None:
    """`for i in range(10**9)` must not be attempted. A refusal is cheap; a hang is not."""
    result = E.evaluate("for i in range(1000000000):\n    print(1)\n")
    assert result["certain"] == []
    assert any("LOOP_TOO_LONG" in reason for reason in result["unknowns"])
