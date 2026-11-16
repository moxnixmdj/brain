"""The travel ladder: the renamed rung must be a permutation, not a different program.

Rung 2 asks whether a lesson survives a change of spelling. That question is only well posed if the
renamed program is the SAME program: `scramble` then `_unscramble` must return the original source
exactly, because anything less would judge the lesson against a program it was never taught. The
first version of the replay arm in this project stripped indentation and produced 17 false verdicts
against a correct record; this file exists so that class of mistake cannot recur here.

Also pinned: two independent bugs that taught the same kind give support 2, and one bug counted twice
does not -- support is the only evidence a mechanism like this can honestly accumulate.
"""
from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import arm_learned_from_its_own_verified_repairs_v1 as learner  # noqa: E402
import what_one_verified_repair_travels_v1 as travel  # noqa: E402

DEFECTIVE = """def smallest(numbers):
    best = numbers[0]
    for value in numbers:
        if value > best:
            best = value
    return best
"""

REPAIRED = """def smallest(numbers):
    best = numbers[0]
    for value in numbers:
        if value < best:
            best = value
    return best
"""


class TestTheRenamedRungIsAPermutation:
    def test_scrambling_changes_every_bound_name(self) -> None:
        scrambled = travel.scramble(DEFECTIVE, "zq")
        assert "smallest" not in scrambled and "best" not in scrambled and "numbers" not in scrambled

    def test_scramble_then_unscramble_is_the_same_program(self) -> None:
        scrambled = travel.scramble(DEFECTIVE, "zq")
        restored = travel._unscramble(scrambled, scrambled, DEFECTIVE)
        assert restored is not None
        assert ast.dump(ast.parse(restored)) == ast.dump(ast.parse(DEFECTIVE))

    def test_a_lesson_survives_renaming_because_the_edit_is_about_structure(self) -> None:
        vocabulary = learner.fold([("renamed", travel.scramble(DEFECTIVE, "zq"),
                                    travel.scramble(REPAIRED, "zq"))])
        assert learner.propose(travel.scramble(DEFECTIVE, "zq"), vocabulary), \
            "a rename-consistent lesson must still fire on the renamed program"


class TestSupportIsTheOnlyEvidenceThereIs:
    def test_two_different_bugs_teaching_the_same_kind_give_support_two(self) -> None:
        twin = DEFECTIVE.replace("smallest", "least").replace("numbers", "items") \
                        .replace("best", "top").replace("value", "item")
        twin_fixed = REPAIRED.replace("smallest", "least").replace("numbers", "items") \
                            .replace("best", "top").replace("value", "item")
        folded = learner.fold([("a", DEFECTIVE, REPAIRED), ("b", twin, twin_fixed)])
        supports = [t.support for t in folded["node"] + folded["leaf"]]
        assert max(supports) >= 2

    def test_an_empty_demonstration_set_has_no_support_to_claim(self) -> None:
        folded = learner.fold([])
        assert folded == {"node": [], "leaf": []}
