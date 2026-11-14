"""Tests for the differential witness search.

The rule these tests obey is the project's own: a test that cannot fail is not a test. Every case
below is one of the instrument's real failure modes from this round, pinned so it cannot come back.
They are hand-written pairs on purpose -- the real-code measurement lives in
`canonical/verification/DIFFERENTIAL_WITNESS_REAL_COMMITS_20261114_V1.json`, and repeating it here
would make the suite slow without making it stronger.
"""

from __future__ import annotations

import ast
import json

from canonical.swe_kernel import differential_witness_v1 as witness


def test_a_boundary_flip_is_found_at_the_boundary() -> None:
    """The input is the boundary value itself, not a value in the same neighbourhood."""
    result = witness.search(
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
    )
    assert result["verdict"] == witness.WITNESS
    assert [w["args"] for w in result["witnesses"]] == [[100]]
    assert result["witness_kinds"] == ["VALUE"]


def test_a_guard_is_found_at_the_value_it_rejects() -> None:
    result = witness.search(
        "def f(x):\n    return x\n",
        'def f(x):\n    if x < 0:\n        raise ValueError("x must be at least 0")\n    return x\n',
    )
    assert result["verdict"] == witness.WITNESS
    assert result["witnesses"][0]["args"] == [-1]
    assert result["strong_witness_count"] == 1


def test_a_genuine_refactor_produces_no_witness() -> None:
    """The verdict that is allowed to be wrong in one direction, and says so in `bounded_search`."""
    result = witness.search(
        "def total(xs):\n    out = 0\n    for x in xs:\n        out += x\n    return out\n",
        "def total(xs):\n    return sum(xs)\n",
    )
    assert result["verdict"] == witness.NO_WITNESS
    assert result["witnesses"] == []


def test_a_speedup_that_is_not_equivalent_is_caught() -> None:
    """A real bug found by this tool on a pair that advertises itself as a pure optimisation."""
    result = witness.search(
        "def triangle(n):\n    return sum(range(n))\n",
        "def triangle(n):\n    return n * (n - 1) // 2\n",
    )
    assert result["verdict"] == witness.WITNESS
    assert result["witnesses"][0]["args"] == [-1]


def test_prose_never_becomes_an_argument() -> None:
    """Literals come from real AST constants; `ast.dump` text turns identifiers into strings.

    Pinned through the PUBLIC path, because a helper-level assertion is not enough: mutation testing
    this round showed the first version of this test still passed when the prose filter was deleted.
    The old pairing harvested literals from `ast.dump` text, so `Name(id='size')` arrived as the
    string "size"; here a docstring-heavy function must never be called with its own docstring.
    """
    source = (
        'def f(x):\n'
        '    """A long prose docstring.\n\n    >>> f(1)\n    1\n    """\n'
        '    return x\n'
    )
    literals = witness._literals(ast.parse(source).body[0])
    assert [value for value in literals if isinstance(value, str) and "\n" in value] == []
    assert "x" not in literals

    result = witness.search(source, source.replace("return x", "return x + 0"))
    for found in result.get("witnesses") or []:
        for argument in found["args"]:
            assert not (isinstance(argument, str) and "\n" in argument), found


def test_a_generator_is_compared_by_content_not_address() -> None:
    """`repr` of a generator contains its address, which made every candidate 'differ'.

    Pinned through the PUBLIC path. Measured: a docs-only commit in more-itertools came back with a
    witness because `set_partitions` returns a generator and the two addresses never match -- an
    assertion on the renderer alone did not catch it.
    """
    rendered = witness._render((value for value in (1, 2)))
    assert "0x" not in rendered
    assert rendered == "generator(1, 2)"

    source = "def items(n):\n    return (x for x in range(n))\n"
    result = witness.search(source, source)
    assert result["verdict"] == witness.NOT_BEHAVIOURAL

    changed = witness.search(source, "def items(n):\n    return [x for x in range(n)]\n")
    for found in changed.get("witnesses") or []:
        assert "0x" not in (found["before_result"] + found["after_result"]), found


def test_an_address_bearing_value_is_not_a_witness() -> None:
    """A registry of objects with default reprs differs only by address; that is unobservable."""

    class Thing:
        pass

    # The renderer replaces a surviving address with "<Type at an address>", so the literal "0x" is
    # gone and a check for "0x" passes anyway. What must be refused is the witness itself.
    result = witness.search("A = [1]\n", "class Thing:\n    pass\nA = [Thing()]\n")
    assert result.get("witnesses") == [], result.get("witnesses")


def test_the_self_check_passes() -> None:
    """The instrument proves its own properties; a red self-check means no verdict is quotable."""
    report = witness.self_check()
    assert report["passed"] is True, json.dumps(
        [check for check in report["checks"] if not check["passed"]], indent=1
    )
    assert report["authority"] == "NONE"
    assert report["count"] >= 7
