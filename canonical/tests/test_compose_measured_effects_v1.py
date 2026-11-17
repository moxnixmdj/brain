"""Composition must be sound, and a refusal must be a proof.

Four ways this could lie, each pinned:

1. It could plan with an operator the measurement did not support -- an atom measured INERT or
   UNCLASSIFIED is not an operator, however useful it would be (`cp` duplicates a content, a shape
   outside the three-effect vocabulary, and is therefore unusable here).
2. It could satisfy a goal while breaking the machine -- "make X disappear" is satisfiable by
   overwriting X with something nobody asked for, so the frame condition must reject that plan.
3. It could call a search budget a proof. When the offered effects cannot reach the goal the search
   must be exhaustive and the verdict must say so; a depth limit is reported as a depth limit.
4. It could trust its own prediction. Every step is compared against what was predicted before it
   ran, and a disagreement is a measurement error rather than a success.
"""
from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import compose_measured_effects_v1 as compose  # noqa: E402
import instant_learning_in_a_new_environment_v1 as instant  # noqa: E402


def library(*rows):
    return [{"atom": atom, "state_class": state_class, "effect": effect, "addressable": addressable}
            for atom, state_class, effect, addressable in rows]


class TestOnlyMeasuredOperators:
    def test_inert_and_unclassified_cells_never_become_operators(self) -> None:
        ops = compose.operators_from(library(("A1", "TARGET_ABSENT", instant.PERSIST, True),
                                             ("A2", "TARGET_EXISTS", instant.INERT, False),
                                             ("A3", "TARGET_EXISTS", instant.UNCLASSIFIED, False)))
        assert [op.atom for op in ops] == ["A1"]

    def test_an_effect_that_ignores_its_argument_is_not_an_operator(self) -> None:
        ops = compose.operators_from(library(("A1", "TARGET_EXISTS", instant.REMOVE, False)))
        assert ops == []


class TestTheFrameCondition:
    def test_overwriting_the_thing_to_remove_breaks_the_frame(self) -> None:
        start = collections.Counter({"old": 1, "keep": 1})
        request = instant.Request(instant.REMOVE, old="old")
        overwritten = collections.Counter({"keep": 1, "nobody_asked": 1})
        assert compose.holds(request, start, overwritten)          # the stated goal is met
        assert not compose.holds_strict(request, start, overwritten)  # and something else moved
        assert compose.holds_strict(request, start, collections.Counter({"keep": 1}))

    def test_side_effects_are_counted_not_ignored(self) -> None:
        start = [("a", "old"), ("b", "keep")]
        now = [("b", "keep"), ("c", "nobody_asked")]
        assert compose._side_effects(instant.Request(instant.REMOVE, old="old"), start, now) == 1


class TestTheSearch:
    def test_two_steps_are_composed_when_the_goal_needs_them(self) -> None:
        ops = compose.operators_from(library(("P", "TARGET_ABSENT", instant.PERSIST, True),
                                             ("D", "TARGET_EXISTS", instant.REMOVE, True)))
        start = collections.Counter({"old": 1})
        request = instant.Request(instant.REPLACE, content="new", old="old")
        result = compose.plan(request, start, ops)
        assert result["status"] == "PLANNED" and len(result["plan"]) == 2

    def test_an_unreachable_goal_is_reported_as_proven_with_the_states_exhausted(self) -> None:
        ops = compose.operators_from(library(("P", "TARGET_ABSENT", instant.PERSIST, True)))
        start = collections.Counter({"old": 1})
        request = instant.Request(instant.REMOVE, old="old")
        result = compose.plan(request, start, ops)
        assert result["status"] == "PROVEN_UNREACHABLE_UNDER_THE_OFFERED_ATOMS"
        assert result["explored"] >= 1

    def test_the_shortest_plan_wins(self) -> None:
        ops = compose.operators_from(library(("R", "TARGET_EXISTS", instant.REPLACE, True),
                                             ("P", "TARGET_ABSENT", instant.PERSIST, True),
                                             ("D", "TARGET_EXISTS", instant.REMOVE, True)))
        start = collections.Counter({"old": 1})
        result = compose.plan(instant.Request(instant.REPLACE, content="new", old="old"), start, ops)
        assert len(result["plan"]) == 1


class TestThePredictionIsAudited:
    def test_a_step_that_did_not_do_what_was_predicted_is_not_a_success(self) -> None:
        operator = compose.Operator("A1", "TARGET_ABSENT", instant.PERSIST, True)
        step = compose.Step(operator, {"content": "new", "old": "old"},
                            collections.Counter({"old": 1, "new": 1}), True)
        assert compose.step_agrees(step, [("a", "old"), ("b", "new")])
        assert not compose.step_agrees(step, [("a", "old")])
