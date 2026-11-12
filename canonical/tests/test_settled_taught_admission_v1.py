#!/usr/bin/env python3
"""Settled admission of taught edits: refuse on one contradiction, admit on full coverage.

PREDICTIONS -- first block written 2026-11-12 BEFORE any run; REVISED block written after
the first confirmatory run falsified the first protocol, and BEFORE the second run. Branch
`arena/8d982436-brain`, base `be081116` (the INSTANT_LEARNING_AUDIT merge).

FIRST PROTOCOL (falsified by run 1): "any disagreement point settles a 2-hypothesis space,
so admission/refusal costs exactly 1 query." Run 1 refuted this on P2: at the first
disagreement point (-1,-1) the oracle legitimately answers False (-1 is no valid index),
apply_teach also says False, and the posterior 'settled' onto the WRONG rule -- the audit's
0/200 one-success result (WHAT_A_SUCCESS_TEACHES), reproduced in miniature by the first
draft of the gate itself. Lesson banked: a coarse two-form hypothesis space settles its
posterior after one agreeing answer; identification and validation are different things.

REVISED PROTOCOL + PREDICTIONS (exact numbers, before run 2). Disagreement set D for the
comparison demo on the grid (-1..3)^2 is the five boundary points (a==hi); for the binop
demo on (-1..3) it is all five points. Asymmetric rule: refuse at the FIRST oracle
contradiction of apply_teach; admit only when every point of D has been asked and agreed.

P1  Raw `edit_by_example` applies the demo to `is_last_index` and is WRONG at the boundary:
    is_last_index(3, 3) -> False where the intended answer is True. (Unchanged; run 1 pass.)
P2  With the real oracle: REFUSE, queries_used == 2 (asked (-1,-1): agree; asked (0,0):
    contradiction), every asked point is a boundary (a == hi), winner keep_target.
P3  Strict-bound target `span_ok`: ADMIT, queries_used == 5 (full coverage of D), text has
    the strict comparison.
P4  Binop demo, target `prior` where it does not transfer: REFUSE at queries_used == 1
    (first point (i=-1): apply 0 vs oracle -1).
P5  Binop demo, target `later` where it does transfer: ADMIT, queries_used == 5.
P6  Disagreement + oracle=None -> REFUSE fail closed; disagreement points recorded; no edit.
P7  Candidates indistinguishable on the whole grid -> ADMIT_GRID_NON_DISCRIMINATING,
    0 queries, honest finite-grid limit in `why`. (Unchanged; run 1 pass.)
P8  Target unprobeable (default `hi=1/0` explodes at exec) -> REFUSE_UNPROBEABLE_TARGET.
P9  Budget 0 with disagreement -> REFUSE, 0 queries, row UNDERDETERMINED, PARTIAL_COVERAGE.
P10 Budget 3 on P3's target (needs 5) -> REFUSE fail closed after 3 agreeing questions --
    partial coverage never admits.

Regression: `edit_by_example_v1.py` is not modified by this round; the pre-existing suite
`test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py` must pass
unchanged (run separately, 49 tests).
"""
from __future__ import annotations

import ast

import pytest

from canonical.runtime.settlement_v1 import SETTLED, UNDERDETERMINED
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe
from canonical.swe_kernel.taught_actions.settled_admission_v1 import (
    ADMIT_GRID_NON_DISCRIMINATING,
    ADMIT_SETTLED,
    REFUSE_NO_ORACLE_UNSETTLED,
    REFUSE_ORACLE_SAYS_KEEP,
    REFUSE_UNPROBEABLE_TARGET,
    REFUSE_UNSETTLED_BY_INSTRUMENT,
    settle_taught_edit,
)

# The exact demonstration measured as defect 6 in one_try_state_probe_20261112_v1.py.
BEFORE = "def inside(a, hi):\n    return a <= hi\n"
AFTER = "def inside(a, hi):\n    return a < hi\n"

IS_LAST_INDEX = "def is_last_index(a, hi):\n    return a <= hi\n"
# A target the demonstration can actually transfer onto still carries the OLD form; a
# target already in the new form has nothing to change and stays REFUSED_SHAPE (tested).
STRICT_INTENDED = "def span_ok(a, hi):\n    return a <= hi\n"


def truth_is_last_index(a: int, hi: int) -> bool:
    """`a` indexes into the inclusive range 0..hi, so the boundary itself is inside."""
    return 0 <= a <= hi


def truth_strict(a: int, hi: int) -> bool:
    return 0 <= a < hi


# Binop family: `- 1` -> `+ 1` taught on `step`. The rule binds names, so the demo uses
# the same parameter name `i` as the targets (a rename-mismatch is correctly REFUSED_SHAPE).
BINO_BEFORE = "def step(i):\n    return i - 1\n"
BINO_AFTER = "def step(i):\n    return i + 1\n"
BINO_KEEP_RIGHT = "def prior(i):\n    return i - 1\n"
BINO_APPLY_RIGHT = "def later(i):\n    return i - 1\n"


def truth_prior(i: int) -> int:
    return i - 1


def truth_later(i: int) -> int:
    return i + 1


def _run(text: str, *args: int) -> object:
    namespace: dict[str, object] = {}
    exec(compile(text, "<t>", "exec"), namespace)  # noqa: S102
    name = next(n for n in namespace if callable(namespace[n]) and not n.startswith("__"))
    return namespace[name](*args)  # type: ignore[operator]


def test_p1_one_try_defect_reproduces_on_this_tree() -> None:
    edited = ebe.edit_by_example(IS_LAST_INDEX, BEFORE, AFTER)
    assert "a < hi" in edited  # the edit was applied ...
    assert _run(edited, 3, 3) is False  # ... and it is WRONG at the boundary


def test_p2_boundary_target_refused_after_two_boundary_questions() -> None:
    result = settle_taught_edit(
        IS_LAST_INDEX, BEFORE, AFTER, oracle=truth_is_last_index
    )
    assert result["action"] == REFUSE_ORACLE_SAYS_KEEP
    assert result["edited_text"] is None
    assert result["settlement"]["status"] == SETTLED
    assert result["settlement"]["queries_used"] == 2
    assert result["settlement"]["winner"] == "keep_target"
    asked = result["probes_asked"]
    assert all(a == hi for a, hi in asked)  # every question is a boundary
    assert (-1, -1) in [tuple(p) for p in asked]  # first: agree (oracle says False too)
    assert (0, 0) in [tuple(p) for p in asked]  # second: contradiction -> refuse
    assert "ORACLE_CONTRADICTS_APPLY" in result["evidence"]


def test_p3_strict_target_admitted_after_full_coverage() -> None:
    result = settle_taught_edit(STRICT_INTENDED, BEFORE, AFTER, oracle=truth_strict)
    assert result["action"] == ADMIT_SETTLED
    assert result["settlement"]["queries_used"] == 5  # every boundary point covered
    assert result["settlement"]["winner"] == "apply_teach"
    assert result["edited_text"] is not None
    assert "a < hi" in result["edited_text"]


def test_p4_binop_family_refused_with_one_question() -> None:
    result = settle_taught_edit(
        BINO_KEEP_RIGHT, BINO_BEFORE, BINO_AFTER, oracle=truth_prior
    )
    assert result["action"] == REFUSE_ORACLE_SAYS_KEEP
    assert result["settlement"]["queries_used"] == 1
    assert result["edited_text"] is None


def test_p5_binop_family_admitted_after_full_coverage() -> None:
    result = settle_taught_edit(
        BINO_APPLY_RIGHT, BINO_BEFORE, BINO_AFTER, oracle=truth_later
    )
    assert result["action"] == ADMIT_SETTLED
    assert result["settlement"]["queries_used"] == 5
    assert result["edited_text"] is not None
    assert "i + 1" in result["edited_text"]


def test_p6_no_oracle_fails_closed_and_records_the_questions() -> None:
    result = settle_taught_edit(IS_LAST_INDEX, BEFORE, AFTER, oracle=None)
    assert result["action"] == REFUSE_NO_ORACLE_UNSETTLED
    assert result["edited_text"] is None
    assert result["disagreement_points"], "the questions worth asking are recorded"
    assert all(a == hi for a, hi in result["disagreement_points"])
    assert "UNSETTLED_NO_ORACLE" in result["evidence"]


def test_p7_non_discriminating_grid_admits_and_says_so() -> None:
    gated = (
        "def gated(a, hi):\n"
        "    if a > 100:\n"
        "        return a <= hi\n"
        "    return False\n"
    )
    result = settle_taught_edit(gated, BEFORE, AFTER, oracle=truth_is_last_index)
    assert result["action"] == ADMIT_GRID_NON_DISCRIMINATING
    assert result["probes_asked"] == []
    assert result["grid_size"] > 0
    assert "GRID_NON_DISCRIMINATING" in result["evidence"]
    assert "finite" in result["why"]  # the honest limit is in the answer itself


def test_p8_unprobeable_target_fails_closed() -> None:
    broken = "def broken(a, hi=1/0):\n    return a <= hi\n"
    result = settle_taught_edit(broken, BEFORE, AFTER, oracle=truth_is_last_index)
    assert result["action"] == REFUSE_UNPROBEABLE_TARGET
    assert result["edited_text"] is None


def test_p9_zero_budget_fails_closed_asking_nothing() -> None:
    result = settle_taught_edit(
        IS_LAST_INDEX, BEFORE, AFTER, oracle=truth_is_last_index, budget=0
    )
    assert result["action"] == REFUSE_UNSETTLED_BY_INSTRUMENT
    assert result["probes_asked"] == []
    assert result["settlement"]["status"] == UNDERDETERMINED
    assert result["settlement"]["queries_used"] == 0
    assert "PARTIAL_COVERAGE" in result["evidence"]


def test_p10_partial_coverage_never_admits() -> None:
    """P3's target needs 5 agreeing questions; 3 agreeing answers must still refuse."""
    result = settle_taught_edit(
        STRICT_INTENDED, BEFORE, AFTER, oracle=truth_strict, budget=3
    )
    assert result["action"] == REFUSE_UNSETTLED_BY_INSTRUMENT
    assert result["settlement"]["queries_used"] == 3
    assert len(result["disagreement_points"]) == 5
    assert result["edited_text"] is None
    assert "PARTIAL_COVERAGE" in result["evidence"]


def test_shape_refusal_unchanged() -> None:
    """A differently-shaped target keeps today's refusal; this module does not loosen it."""
    different = "def is_last_index(i, n):\n    return i <= n - 1\n"
    with pytest.raises(ebe.Refused):
        ebe.edit_by_example(different, BEFORE, AFTER)
    result = settle_taught_edit(different, BEFORE, AFTER, oracle=truth_is_last_index)
    assert result["action"] == "REFUSED_SHAPE"
