"""Round 18: the changed condition names the value it wants; deliver it at the type that can carry it.

The first fixture is the fire proof, and it is chosen so that NO string mutation can pass: the guard compares a
dict's keys with a set of names that appear nowhere in the test or in the pre-fix file, and the function refuses
anything that is not a mapping before the comparison is reached. Only reading the operands the program actually
compared -- and delivering them keyed -- gets there.

The second fixture is the honesty proof: the gate is a CALL (`isinstance`), not a comparison, so nothing is
logged and the instrument must say it had no executed comparison to read, never that the part is unreachable.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import what_the_condition_wants_v1 as W  # noqa: E402

DEFECTIVE = '''def parse(state):
    return len(state)
'''

KEYS_FIXED = '''def parse(state):
    if not isinstance(state, dict):
        raise ValueError("not a mapping")
    if state.keys() >= {"alpha", "beta"}:
        raise ValueError("both keys")
    return len(state)
'''

CALL_GATED_FIXED = '''def parse(state):
    if not isinstance(state, dict):
        raise ValueError("not a mapping")
    if len(state) > 2:
        raise ValueError("too many")
    return len(state)
'''

TEST = '''import pytest
from mod import parse


def test_len():
    assert parse({"gamma": 1}) == 1
'''

TEST_STR_ONLY = '''import pytest
from mod import parse


def test_text():
    assert parse("gamma") == 5
'''


def _part(defective: str, fixed: str):
    from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS
    return next(part for part in PINS.hunks(defective, fixed)
                if PINS.is_behavioural(fixed, part) and not PINS.typing_only(fixed, part))


def test_a_value_the_program_compared_is_delivered_and_pins_the_part(tmp_path):
    (tmp_path / "mod.py").write_text(DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    part = _part(DEFECTIVE, KEYS_FIXED)
    mutant = W.SYN._assertion  # keep the import honest: SYN is the assertion renderer reused here
    from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS
    revert = PINS.revert(KEYS_FIXED, DEFECTIVE, part)
    calls = W.SYN.calls_from_the_test(TEST)
    assert calls, "the test's literal call must be recovered"
    verdict = W.what_the_condition_wants(tmp_path, "mod.py", "test_mod.py", KEYS_FIXED, revert, part, calls)
    assert verdict["state"] == W.PINNED, verdict
    assert "pytest.raises" in verdict["assertion"]
    assert (tmp_path / "mod.py").read_text(encoding="utf-8") == DEFECTIVE   # always restored


def test_a_gate_that_is_a_call_is_seen_and_rerolled_rather_than_called_unreachable(tmp_path):
    (tmp_path / "mod.py").write_text(DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST_STR_ONLY, encoding="utf-8")
    part = _part(DEFECTIVE, CALL_GATED_FIXED)
    from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS
    revert = PINS.revert(CALL_GATED_FIXED, DEFECTIVE, part)
    calls = W.SYN.calls_from_the_test(TEST_STR_ONLY)
    verdict = W.what_the_condition_wants(tmp_path, "mod.py", "test_mod.py", CALL_GATED_FIXED, revert, part, calls)
    # `isinstance(...)` is a call, not a comparison: CmpLog hooks strcmp/memcmp for this reason, and so does this
    # instrument. The gate is SEEN, the shape it rejected is rerolled (a string seed becomes a mapping keyed by its
    # own characters), the guard behind it then fires, and the part is pinned. Measured, not asserted: the reroll
    # is what turns a call gate from a refusal into a pin.
    assert verdict["state"] == W.PINNED, verdict
    assert verdict["gates_passed"] >= 1


def test_the_prelude_offset_is_measured_not_assumed():
    # the traced child reports lines of the INSTRUMENTED file; this offset is what maps them back
    offset = W._prelude_offset()
    instrumented, _, _ = W._instrument("def f(a, b):\n    return a > b\n", 1, 9)
    assert any("__a1 := a" in line for line in instrumented.splitlines()[offset:offset + 2])


def test_instrumentation_preserves_the_result_of_every_comparison():
    source = "def f(a, b):\n    if a >= b:\n        return a - b\n    return b - a\n"
    instrumented, rewritten, skipped = W._instrument(source, 1, 9)
    assert rewritten == 1 and skipped == 0
    plain, logged = {}, {}
    exec(source, plain)                     # noqa: S102 - a fixture, not untrusted input
    exec(instrumented, logged)              # noqa: S102
    for a, b in ((1, 2), (3, 3), (5, 2)):
        assert plain["f"](a, b) == logged["f"](a, b)


def test_a_chained_comparison_is_counted_and_left_alone():
    instrumented, rewritten, skipped = W._instrument("x = 1\nif 0 < x < 5:\n    pass\n", 1, 3)
    assert rewritten == 0 and skipped == 1
    assert "0 < x < 5" in instrumented


def test_the_wanted_operand_is_the_one_the_input_does_not_determine():
    seed = "gamma"
    entries = [{"tag": "cmp1@L3", "a": ["str", "gamma"], "b": ["str", "alpha"]}]
    assert W._wanted(entries, [seed]) == ["alpha"]
    same = [{"tag": "cmp1@L3", "a": ["str", "gamma"], "b": ["str", "gamma"]}]
    assert W._wanted(same, [seed]) == []      # both sides come from the input: nothing is wanted
