"""Round 17: generate the input that reaches a changed line, then assert what happens there.

The two fixtures are the fire proof and the honesty proof. The first guard is reachable by mutation (length),
so a `PINNED` result proves the directed loop closes. The second guard triggers on a character that appears
nowhere in the test or the module, so the alphabet cannot contain it and the instrument must say
`NOT_REACHED` -- a search that fails must report a failed search, never an absence of behaviour.
"""

from __future__ import annotations

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import reach_the_changed_site_v1 as R  # noqa: E402

REACHABLE_DEFECTIVE = '''def parse(text):
    if not text:
        raise ValueError("empty")
    return len(text)
'''

REACHABLE_FIXED = '''def parse(text):
    if not text:
        raise ValueError("empty")
    if len(text) > 12:
        raise ValueError("too long")
    return len(text)
'''

SILENT_FIXED = '''def parse(text):
    if not text:
        raise ValueError("empty")
    if len(text) > 12:
        pass
    return len(text)
'''

UNREACHABLE_FIXED = '''def parse(text):
    if not text:
        raise ValueError("empty")
    if text == "!!!!":
        raise ValueError("four bangs")
    return len(text)
'''

TEST = '''import pytest
from mod import parse


def test_empty():
    with pytest.raises(ValueError):
        parse("")
'''

TEST_CALLS = '''import pytest
from mod import parse


def test_empty():
    with pytest.raises(ValueError):
        parse("")


def test_short():
    assert parse("abc") == 3
'''


def _repo(tmp_path: pathlib.Path, fixed: str) -> pathlib.Path:
    (tmp_path / "mod.py").write_text(REACHABLE_DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST_CALLS, encoding="utf-8")
    return tmp_path


def _part(defective: str, fixed: str):
    from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS
    return next(part for part in PINS.hunks(defective, fixed)
                if PINS.is_behavioural(fixed, part) and not PINS.typing_only(fixed, part))


def test_a_reachable_guard_is_reached_and_the_assertion_is_verified(tmp_path):
    tree = _repo(tmp_path, REACHABLE_FIXED)
    part = _part(REACHABLE_DEFECTIVE, REACHABLE_FIXED)
    mutant = R.PINS.revert(REACHABLE_FIXED, REACHABLE_DEFECTIVE, part)
    calls = R.SYN.calls_from_the_test((tree / "test_mod.py").read_text())
    # the suite passes on the mutant, which is what "unpinned" means
    (tree / "mod.py").write_text(mutant, encoding="utf-8")
    assert G.run_test(tree, "test_mod.py")["passed"] is True
    verdict = R.reach_part(tree, "mod.py", "test_mod.py", REACHABLE_FIXED, mutant, part, calls, budget=60)
    assert verdict["state"] == R.PINNED
    assert verdict["executions"] > 0
    assert "pytest.raises" in verdict["assertion"]      # the receipt must contain the assertion, not its last line
    assert (tree / "mod.py").read_text(encoding="utf-8") == mutant      # always restored


def test_a_trigger_outside_the_alphabet_is_reported_as_not_reached(tmp_path):
    tree = _repo(tmp_path, UNREACHABLE_FIXED)
    part = _part(REACHABLE_DEFECTIVE, UNREACHABLE_FIXED)
    mutant = R.PINS.revert(UNREACHABLE_FIXED, REACHABLE_DEFECTIVE, part)
    calls = R.SYN.calls_from_the_test((tree / "test_mod.py").read_text())
    verdict = R.reach_part(tree, "mod.py", "test_mod.py", UNREACHABLE_FIXED, mutant, part, calls, budget=40)
    assert verdict["state"] == R.NOT_REACHED
    assert verdict["executions"] >= 30


def test_reaching_a_line_without_changing_the_outcome_is_not_a_pin(tmp_path):
    tree = _repo(tmp_path, SILENT_FIXED)
    part = _part(REACHABLE_DEFECTIVE, SILENT_FIXED)
    mutant = R.PINS.revert(SILENT_FIXED, REACHABLE_DEFECTIVE, part)
    calls = R.SYN.calls_from_the_test((tree / "test_mod.py").read_text())
    verdict = R.reach_part(tree, "mod.py", "test_mod.py", SILENT_FIXED, mutant, part, calls, budget=60)
    assert verdict["state"] in (R.REACHED_NO_DIFF, R.NOT_REACHED)


def test_a_part_that_only_removes_code_is_refused_not_searched():
    # a deletion adds no line, so there is no line to reach; the deleted statement lives only in the mutant
    part = {"added": "", "removed": "if x:", "new": (4, 4)}
    verdict = R.reach_part(pathlib.Path("/nonexistent"), "m.py", "t.py", "x\n", "x\n", part, [], budget=1)
    assert verdict["state"] == R.REFUSED_REMOVAL and verdict["executions"] == 0


def test_the_gradient_comes_from_quantities_compared_against_in_the_changed_block():
    assert R._hints('    if len(text) > 12:\n        raise ValueError("too long")') == [12]
    assert R._hints('    raise ValueError("no quantities here")') == []
    assert R._distance("abc", [12]) == 9 and R._distance("abc", []) is None


def test_mutation_is_deterministic_for_a_given_seed():
    first = [R._mutate("abc", ".:", random.Random(7)) for _ in range(5)]
    second = [R._mutate("abc", ".:", random.Random(7)) for _ in range(5)]
    assert first == second


def test_the_alphabet_is_harvested_from_the_artifact_not_written_by_hand():
    alphabet = R._alphabet("assert x == 'a:b'", "if x: pass")
    assert ":" in alphabet and "=" in alphabet and "!" not in alphabet
