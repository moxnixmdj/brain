"""A plan gate must be able to reject the plan it was written for.

The owner's four-phase plan is recorded in canonical/research_sources/PROPOSED_PLAN_20261113_V1.json.
These tests pin that it is refused, that it is refused for every reason it is actually defective,
and -- symmetrically -- that a plan carrying all five requirements is admitted. A gate that refuses
everything is not a gate; it is an obstacle, and it would have been the wrong thing to build.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools.plan_admission_v1 import (  # noqa: E402
    CODES,
    DEFAULT_PLAN,
    check_plan,
    load,
)


def _phase(**over: object) -> dict:
    base = {
        "name": "Phase 1: verifier-backed edit class on an unseen repository",
        "actions": ["edit_file", "run_tests"],
        "success_criterion": "held-out coverage and precision on a repository never used to design the operators",
        "held_out": "8 merged pull requests from repositories the operators were not designed on",
        "controls": ["cache-only arm", "random arm"],
        "stopping_rule": "stop at 240 askings per arm, or when the held-out curve is flat for 40 askings",
        "falsifier": "the cache-only arm comes within 5 points of coverage at equal precision",
    }
    base.update(over)
    return base


def _plan(*phases: dict) -> dict:
    return {"schema": "proposed_plan_v1", "phases": list(phases) or [_phase()]}


# ---------------------------------------------------------------------------------------------
# The plan this gate was written for
# ---------------------------------------------------------------------------------------------
def test_the_owners_four_phase_plan_is_refused() -> None:
    assert check_plan(load(DEFAULT_PLAN)).admitted is False


def test_it_is_refused_for_every_reason_it_is_actually_defective() -> None:
    codes = {f.code for f in check_plan(load(DEFAULT_PLAN)).blocking}
    for expected in (
        "ACTIVITY_METRIC",
        "NO_RATIO",
        "NO_HELD_OUT",
        "NO_CACHE_CONTROL",
        "NO_RANDOM_CONTROL",
        "NO_STOPPING_RULE",
        "NO_FALSIFIER",
        "ACTION_IS_A_TASK_FAMILY",
    ):
        assert expected in codes, f"{expected} not raised; raised {sorted(codes)}"


def test_the_refusal_names_the_causal_model_count() -> None:
    """The specific defect: '10 causal models -> 25 -> 40' is an artefact count, not capability."""
    details = " ".join(f.detail for f in check_plan(load(DEFAULT_PLAN)).blocking)
    assert "causal model" in details


def test_a_domain_ordered_plan_is_only_a_note_not_a_refusal() -> None:
    """Ordering by substrate is a bad idea, but it is not by itself a reason to block work."""
    plan = _plan(_phase(name="Phase 1: code edits first, then GUI applications"))
    verdict = check_plan(plan)
    assert verdict.admitted is True
    assert any(f.code == "DOMAIN_SEQUENCING" for f in verdict.findings)


# ---------------------------------------------------------------------------------------------
# Symmetry: a plan that carries the five requirements passes
# ---------------------------------------------------------------------------------------------
def test_a_plan_with_all_five_requirements_is_admitted() -> None:
    assert check_plan(_plan()).admitted is True


def test_each_missing_requirement_turns_admitted_into_refused() -> None:
    mutations = {
        "NO_HELD_OUT": {"held_out": "   "},
        "NO_CACHE_CONTROL": {"controls": ["random arm"]},
        "NO_RANDOM_CONTROL": {"controls": ["cache-only arm"]},
        "NO_STOPPING_RULE": {"stopping_rule": ""},
        "NO_FALSIFIER": {"falsifier": ""},
        "NO_RATIO": {"success_criterion": "the system gets better at refactoring"},
    }
    for expected, over in mutations.items():
        verdict = check_plan(_plan(_phase(**over)))
        assert verdict.admitted is False, expected
        assert expected in {f.code for f in verdict.blocking}, (expected, [f.code for f in verdict.findings])


def test_an_artefact_count_refuses_a_plan_that_has_every_other_requirement() -> None:
    verdict = check_plan(_plan(_phase(success_criterion="builds 40 concepts and keeps them, coverage 90%")))
    assert verdict.admitted is False
    assert "ACTIVITY_METRIC" in {f.code for f in verdict.blocking}


def test_a_task_family_cannot_be_given_as_an_action() -> None:
    verdict = check_plan(_plan(_phase(actions=["edit_file", "multi-step debugging"])))
    assert verdict.admitted is False
    assert "ACTION_IS_A_TASK_FAMILY" in {f.code for f in verdict.blocking}


def test_a_real_action_passes() -> None:
    for action in ("edit_file", "run_tests", "read_file", "apply_patch"):
        assert check_plan(_plan(_phase(actions=[action]))).admitted is True, action


# ---------------------------------------------------------------------------------------------
# Fails closed on malformed input
# ---------------------------------------------------------------------------------------------
def test_a_plan_in_the_wrong_schema_is_refused() -> None:
    assert check_plan({"schema": "something_else", "phases": [_phase()]}).admitted is False


def test_a_plan_with_no_phases_is_refused() -> None:
    assert check_plan({"schema": "proposed_plan_v1", "phases": []}).admitted is False


def test_every_emitted_code_has_an_explanation() -> None:
    emitted = {f.code for f in check_plan(load(DEFAULT_PLAN)).findings}
    emitted |= {f.code for f in check_plan(_plan()).findings}
    assert emitted <= set(CODES), sorted(emitted - set(CODES))


def test_checking_a_plan_does_not_mutate_it() -> None:
    plan = _plan()
    before = copy.deepcopy(plan)
    check_plan(plan)
    assert plan == before
