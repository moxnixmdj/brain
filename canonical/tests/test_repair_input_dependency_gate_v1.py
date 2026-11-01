"""The gate that refuses a repair which stops reading its inputs.

It exists because of a measured false success: a two-file coupled bug "repaired" by a lookup
table that passes the visible tests and discards the data (see
`test_closed_loop_repair_must_generalise_v1.py`). The gate is enforced at candidate admission in
`solve_repository_closed_loop`, and that took honest repairs from **0/5 to 5/5**.

The rule is narrow on purpose: a patch may not reduce a function's input dependency set. These
tests pin both directions -- it must refuse the lookup table, and it must NOT refuse honest
edits, or it will simply block all repair.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import repair_input_dependency_gate_v1 as gate_mod  # noqa: E402

BEFORE = (
    "from billing.discounts import apply_discount\n"
    "\n"
    "def compute_invoice(items: list[float], disc: float) -> float:\n"
    "    total = 0.0\n"
    "    for i in range(len(items) - 1):\n"
    "        total += items[i]\n"
    "    return apply_discount(total, disc)\n"
)

LOOKUP_TABLE = (
    "from billing.discounts import apply_discount\n"
    "\n"
    "def compute_invoice(items: list[float], disc: float) -> float:\n"
    "    if disc % 2 == 0:\n"
    "        return 110.0\n"
    "    return 85.0\n"
)

HONEST = (
    "from billing.discounts import apply_discount\n"
    "\n"
    "def compute_invoice(items: list[float], disc: float) -> float:\n"
    "    total = 0.0\n"
    "    for i in range(len(items)):\n"
    "        total += items[i]\n"
    "    return apply_discount(total, disc)\n"
)


# --------------------------------------------------------------------------- it refuses
def test_the_lookup_table_is_refused():
    verdict = gate_mod.gate(BEFORE, LOOKUP_TABLE)
    assert verdict["status"] == gate_mod.REFUSED
    assert "compute_invoice(items)" in verdict["reason"]


def test_dropping_one_of_two_parameters_is_refused():
    after = (
        "def f(a, b):\n"
        "    return a * 2\n"
    )
    assert gate_mod.lost_dependencies("def f(a, b):\n    return a + b\n", after) == [
        {"function": "f", "parameter": "b"}
    ]


def test_unparseable_source_is_refused_not_guessed():
    verdict = gate_mod.gate(BEFORE, "def compute_invoice(:\n    return 1\n")
    assert verdict["status"] == gate_mod.REFUSED
    assert verdict["reason"] == "SOURCE_NOT_PARSEABLE"


# --------------------------------------------------------------------------- it allows
def test_an_honest_repair_passes():
    assert gate_mod.gate(BEFORE, HONEST)["status"] == gate_mod.PASS


def test_an_unchanged_function_passes():
    assert gate_mod.gate(BEFORE, BEFORE)["status"] == gate_mod.PASS


def test_reformatted_code_that_still_reads_inputs_passes():
    reformatted = (
        "def compute_invoice(items, disc):\n"
        "    return apply_discount(sum(items), disc)\n"
    )
    assert gate_mod.gate(BEFORE, reformatted)["status"] == gate_mod.PASS


def test_a_new_function_with_unused_parameters_passes():
    """The rule is about losing a dependency, not about never having one."""
    before = "def f(a):\n    return a\n"
    after = "def f(a):\n    return a\n\n\ndef g(b):\n    return 1\n"
    assert gate_mod.gate(before, after)["status"] == gate_mod.PASS


def test_a_deleted_function_is_not_this_gate_s_question():
    before = "def f(a):\n    return a\n\n\ndef g(b):\n    return b\n"
    after = "def f(a):\n    return a\n"
    assert gate_mod.gate(before, after)["status"] == gate_mod.PASS


# --------------------------------------------------------------------------- mechanics
def test_nested_function_parameters_are_not_attributed_outward():
    source = (
        "def outer(items):\n"
        "    def inner(x):\n"
        "        return x\n"
        "    return inner(1)\n"
    )
    uses = gate_mod.parameter_use(source)
    assert uses["outer"] == frozenset()
    assert uses["inner"] == frozenset({"x"})


def test_varargs_and_kwargs_are_tracked():
    source = "def f(*args, **kwargs):\n    return len(args) + len(kwargs)\n"
    assert gate_mod.parameter_use(source)["f"] == frozenset({"args", "kwargs"})


def test_the_verdict_carries_no_authority():
    for verdict in (gate_mod.gate(BEFORE, HONEST), gate_mod.gate(BEFORE, LOOKUP_TABLE)):
        assert verdict["terminal_authority"] is False
        assert verdict["schema"] == gate_mod.SCHEMA


def test_empty_source_is_refused():
    with pytest.raises(gate_mod.GateError):
        gate_mod.parameter_use("   ")
