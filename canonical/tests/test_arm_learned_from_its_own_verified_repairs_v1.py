"""Learning from its own verified repairs: nothing from nothing, and only bound names may move.

The two claims these tests pin are the two ways this arm could lie:

1. It could propose candidates before it has been taught anything -- `fold([])` must be empty, so an
   empty vocabulary cannot look like a productive one.
2. It could claim an invariance it does not have. α-renaming is only sound over BOUND names; a global,
   an imported module or a builtin is free, and renaming one would change which computation the
   program denotes. `_bound_names` must therefore name exactly the bound ones, `alpha_canonical` must
   round-trip through `alpha_restore`, and the mechanism must be shown live by firing on the source it
   was taught from -- otherwise a zero on other bugs would mean "broken" instead of "did not travel".
"""
from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import arm_learned_from_its_own_verified_repairs_v1 as learner  # noqa: E402

DEFECTIVE = """import math


def scale(values, factor):
    total = 0
    for value in values:
        total += value * factor
    return math.floor(total)
"""

REPAIRED = """import math


def scale(values, factor):
    total = 0
    for value in values:
        total += value
    return math.floor(total)
"""


class TestNothingComesFromNothing:
    def test_an_empty_vocabulary_proposes_nothing(self) -> None:
        vocabulary = learner.fold([])
        assert vocabulary["node"] == [] and vocabulary["leaf"] == []
        assert learner.propose(DEFECTIVE, vocabulary) == []


class TestOnlyBoundNamesMayMove:
    def test_bound_names_are_exactly_the_ones_the_function_introduces(self) -> None:
        function = next(n for n in ast.parse(DEFECTIVE).body if isinstance(n, ast.FunctionDef))
        bound = learner._bound_names(function)
        assert bound[:3] == ["values", "factor", "total"]  # parameters, then the first assignment
        assert "math" not in bound  # an imported module is free
        assert "floor" not in bound  # an attribute of a free name is free

    def test_canonicalization_round_trips_to_the_same_program(self) -> None:
        canonical, reverse = learner.alpha_canonical(DEFECTIVE)
        assert "values" not in canonical and "math" in canonical
        # unparse collapses blank lines, so the equality that matters is the AST's, not the text's
        back = ast.parse(learner.alpha_restore(canonical, reverse))
        assert ast.dump(back) == ast.dump(ast.parse(DEFECTIVE))

    def test_the_same_program_canonicalizes_the_same_way_however_it_is_spelled(self) -> None:
        twin = DEFECTIVE.replace("values", "items").replace("factor", "k").replace("total", "acc")
        assert learner.alpha_canonical(DEFECTIVE)[0] == learner.alpha_canonical(twin)[0]

    def test_restoration_refuses_a_name_it_was_not_taught(self) -> None:
        canonical, reverse = learner.alpha_canonical(DEFECTIVE)
        broken = canonical.replace("n2", "not_a_name")
        assert "not_a_name" in learner.alpha_restore(broken, reverse)  # unknown names stay literal


class TestTheMechanismIsLive:
    def test_a_lesson_fires_on_the_program_it_was_taught_from(self) -> None:
        vocabulary = learner.fold([("scale", DEFECTIVE, REPAIRED)])
        assert learner.propose(DEFECTIVE, vocabulary), "the kernel proposed nothing on its own bug"

    def test_the_same_lesson_is_what_gives_zero_on_other_bugs_not_a_broken_fold(self) -> None:
        # a lesson that fires where it was taught and nowhere else: the control the note rests on
        vocabulary = learner.fold([("scale", DEFECTIVE, REPAIRED)])
        unrelated = "def other(x):\n    return sorted(x)\n"
        assert learner.propose(unrelated, vocabulary) == []
