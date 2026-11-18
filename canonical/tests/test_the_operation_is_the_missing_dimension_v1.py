"""Round 20: the same seeds, a different verb.

The fire proof is built so that only the OPERATION can explain the difference. Both states return an object from
`make("a")`, both objects repr the same way (identity masked), and the test file asserts only on that call. The
fix changes what `copy.copy(x) == x` means -- so the pin exists in the operation dimension and nowhere else.

The honesty proof is the mirror: a fix that changes `__add__`, which is not in the protocol alphabet this round
uses, must be reported as unreached rather than guessed at.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import the_operation_is_the_missing_dimension_v1 as O  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

DEFECTIVE = '''class Thing:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self is other


def make(name):
    return Thing(name)
'''

FIXED = '''class Thing:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Thing) and self.name == other.name


def make(name):
    return Thing(name)
'''

TEST = '''from mod import make


def test_one():
    assert make("a").name == "a"
'''

UNREACHABLE = '''class Thing:
    def __init__(self, name):
        self.name = name

    def __add__(self, other):
        return Thing(self.name + other.name)


def make(name):
    return Thing(name)
'''

UNREACHABLE_FIXED = UNREACHABLE.replace("self.name + other.name", "self.name + other.name + '!'")


def _tree(tmp_path: pathlib.Path, source: str) -> pathlib.Path:
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def _part(defective: str, fixed: str):
    return next(part for part in PINS.hunks(defective, fixed)
                if PINS.is_behavioural(fixed, part) and not PINS.typing_only(fixed, part))


def test_one_operation_over_the_tests_own_seed_pins_what_the_call_cannot(tmp_path):
    tree = _tree(tmp_path, DEFECTIVE)
    part = _part(DEFECTIVE, FIXED)
    mutant = PINS.revert(FIXED, DEFECTIVE, part)
    seeds = O.seeds_from_calls(SYN.calls_from_the_test(TEST))
    assert seeds and seeds[0]["function"] == "make"
    verdict = O.judge_part(tree, "mod.py", "test_mod.py", FIXED, mutant, seeds)
    assert verdict["state"] == O.R.PINNED, verdict
    assert verdict["pin"]["op"] == "eq_copy"
    assert "copy.copy" in verdict["pin"]["assertion"]


def test_a_change_no_operation_in_the_alphabet_touches_is_reported_unreached(tmp_path):
    tree = _tree(tmp_path, UNREACHABLE)
    part = _part(UNREACHABLE, UNREACHABLE_FIXED)
    mutant = PINS.revert(UNREACHABLE_FIXED, UNREACHABLE, part)
    seeds = O.seeds_from_calls(SYN.calls_from_the_test(TEST))
    verdict = O.judge_part(tree, "mod.py", "test_mod.py", UNREACHABLE_FIXED, mutant, seeds)
    assert verdict["state"] != O.R.PINNED
    assert verdict["differences"] == 0


def test_the_probers_helpers_are_imported_not_redefined():
    assert "def canon(" in O.HELPERS and "def shape_value(" in O.HELPERS
    assert "for item in REQUEST" not in O.HELPERS      # the other module's own loop is not executed twice


def test_seed_tokens_round_trip_to_literals():
    calls = [{"module": "m", "function": "f", "args": ["a", 2]}]
    seeds = O.seeds_from_calls(calls)
    assert seeds[0]["args"] == ["=a", "@json:2"]
    assert O._literal("=a") == "'a'" and O._literal("@json:2") == "2"


def test_the_pin_is_verified_against_both_states_and_the_tree_is_restored(tmp_path):
    tree = _tree(tmp_path, DEFECTIVE)
    part = _part(DEFECTIVE, FIXED)
    mutant = PINS.revert(FIXED, DEFECTIVE, part)
    seeds = O.seeds_from_calls(SYN.calls_from_the_test(TEST))
    verdict = O.judge_part(tree, "mod.py", "test_mod.py", FIXED, mutant, seeds)
    assert "import pytest" in verdict["pin"]["assertion"] and "as _make" in verdict["pin"]["assertion"]
    assert not (tree / O.PIN_TEST_NAME).exists()          # the pin file never survives the judgement
    assert (tree / "mod.py").read_text(encoding="utf-8") == DEFECTIVE   # and the tree was restored
