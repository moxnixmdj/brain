"""Round 16: the missing assertion cannot be recovered from the tests' own inputs -- and the instrument can fire.

The fire proof matters more than the corpus number. The fixture below has a fix that changes ONLY an error
message while the suite asserts only the exception type: the part is unpinned (round 15), the tests' own
input reaches it, and the synthesised assertion must be green on the fix and red on the mutant.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402

DEFECTIVE = '''def load(text):
    if "=" not in text:
        raise ValueError("bad statement")
    return text


def unused_branch(flag):
    if flag:
        raise KeyError("never reached by any test")
    return flag
'''

REPAIRED = '''def load(text):
    if "=" not in text:
        raise ValueError("bad statement (at line 1)")
    return text


def unused_branch(flag):
    if flag:
        raise KeyError("never reached by any test (at col 2)")
    return flag
'''

TEST = '''import pytest
from mod import load


def test_bad():
    with pytest.raises(ValueError):
        load("abc")
'''

TEST_CALLS = '''import tomli
from tomli import loads

tomli.loads("val=.")
loads(s="a=1")
tomli.loads(variable)
'''


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "mod.py").write_text(DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def test_calls_are_taken_from_the_tests_own_imports_and_literals():
    calls = SYN.calls_from_the_test(TEST_CALLS)
    found = {(call["module"], call["function"], tuple(call["args"])) for call in calls}
    assert ("tomli", "loads", ("val=.",)) in found
    assert all(call["args"] and isinstance(call["args"][0], str) for call in calls if call["module"] == "tomli")


def test_a_variable_argument_is_not_a_literal_and_is_skipped():
    calls = SYN.calls_from_the_test('import tomli\ntomli.loads(variable)\n')
    assert calls == []


def test_an_assertion_is_only_built_from_an_outcome_it_can_express():
    assert SYN._assertion({"module": "m", "function": "f", "args": ["x"]}, "RAISED:ValueError:bad") is not None
    assert SYN._assertion({"module": "m", "function": "f", "args": ["x"]}, "UNSTABLE:RAISED:ValueError:x") is None
    assert SYN._assertion({"module": "m", "function": "f", "args": ["x"]}, "MISSING") is None


def test_the_instrument_pins_a_message_the_suite_never_asserted(tmp_path):
    tree = _repo(tmp_path)
    parts = SYN.PINS.hunks(DEFECTIVE, REPAIRED)
    message_part = next(part for part in parts if "at line 1" in part["added"])
    mutant = SYN.PINS.revert(REPAIRED, DEFECTIVE, message_part)
    # the suite passes on the mutant: that is what "unpinned" means
    from canonical.swe_kernel import history_induced_edit_grammar_v1 as G
    (tree / "mod.py").write_text(mutant, encoding="utf-8")
    assert G.run_test(tree, "test_mod.py")["passed"] is True
    calls = SYN.calls_from_the_test(TEST)
    verdict = SYN.pin_part(tree, "mod.py", "test_mod.py", REPAIRED, mutant, calls)
    assert verdict["state"] == SYN.PINNED_BY_SYNTHESIS
    assert "at line 1" in verdict["outcome"]          # the observable that pinned it is the message
    assert (tree / "mod.py").read_text(encoding="utf-8") == mutant      # always restored


def test_a_part_no_test_reaches_is_reported_not_pinned(tmp_path):
    tree = _repo(tmp_path)
    parts = SYN.PINS.hunks(DEFECTIVE, REPAIRED)
    unreached = next(part for part in parts if "at col 2" in part["added"])
    mutant = SYN.PINS.revert(REPAIRED, DEFECTIVE, unreached)
    calls = SYN.calls_from_the_test(TEST)
    verdict = SYN.pin_part(tree, "mod.py", "test_mod.py", REPAIRED, mutant, calls)
    assert verdict["state"] == SYN.NOT_PINNED
    assert verdict["differences"] == 0
