"""Round 21: does the author's own sentence specify the behaviour, or only name it?

The fire proof separates the two columns. The statement quotes the exact input the fix must reject and names the
exception -- and the test's own literals never reach that input. The pin is built from the STATEMENT ALONE, then
verified: it passes on the fixed file and fails on the file with the part reverted.

The honesty proof is the statement that only says something vague: it must be reported as quoting nothing, not
turned into a guess.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import the_smallest_question_that_makes_this_checkable_v1 as Q  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

DEFECTIVE = '''def parse(text):
    return len(text)
'''

FIXED = '''def parse(text):
    if text == "beta-omega":
        raise ValueError("reserved token")
    return len(text)
'''

TEST = '''from mod import parse


def test_one():
    assert parse("a") == 1
'''


def _tree(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "mod.py").write_text(DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def _part():
    return next(part for part in PINS.hunks(DEFECTIVE, FIXED)
                if PINS.is_behavioural(FIXED, part) and not PINS.typing_only(FIXED, part))


def _seeds():
    return [{"module": call["module"], "function": call["function"]}
            for call in SYN.calls_from_the_test(TEST)]


def test_a_quoted_literal_in_the_statement_becomes_the_discriminating_input(tmp_path):
    tree = _tree(tmp_path)
    statement = 'Fix: parse("beta-omega") must now raise ValueError for the reserved token'
    tokens = Q.tokens_of(statement, FIXED)
    assert tokens["quoted"] == ["beta-omega"] and "ValueError" in tokens["exceptions"]
    part = _part()
    mutant = PINS.revert(FIXED, DEFECTIVE, part)
    verdict = Q.judge_part(tree, "mod.py", FIXED, mutant, tokens, _seeds(), FIXED)
    assert verdict["state"] == "SPECIFIED", verdict
    assert verdict["pin"]["input"] == "beta-omega"
    assert "pytest.raises(ValueError)" in verdict["pin"]["assertion"]


def test_a_statement_that_quotes_nothing_is_refused_rather_than_guessed(tmp_path):
    tree = _tree(tmp_path)
    tokens = Q.tokens_of("Improve parse validation and tidy the module", FIXED)
    assert tokens["quoted"] == []
    verdict = Q.judge_part(tree, "mod.py", FIXED, DEFECTIVE, tokens, _seeds(), FIXED)
    assert verdict["state"] == "REFUSED__STATEMENT_QUOTES_NOTHING"


def test_a_quotation_both_states_treat_alike_specifies_nothing(tmp_path):
    tree = _tree(tmp_path)
    tokens = Q.tokens_of('Fix: parse("plain") keeps working', FIXED)
    part = _part()
    mutant = PINS.revert(FIXED, DEFECTIVE, part)
    verdict = Q.judge_part(tree, "mod.py", FIXED, mutant, tokens, _seeds(), FIXED)
    assert verdict["state"] == "NAMED_ONLY" and verdict["differences"] == 0


def test_tokens_are_filtered_to_what_the_artifact_knows():
    statement = 'Fix parse so that parse("xy") raises ValueError, see also Nonsense and COBOL'
    tokens = Q.tokens_of(statement, FIXED)
    assert "parse" in tokens["identifiers"]
    assert "Nonsense" not in tokens["identifiers"] and "COBOL" not in tokens["identifiers"]
    assert tokens["quoted"] == ["xy"]


def test_the_tree_is_restored_and_no_pin_file_survives(tmp_path):
    tree = _tree(tmp_path)
    tokens = Q.tokens_of('Fix: parse("beta-omega") raises ValueError', FIXED)
    part = _part()
    mutant = PINS.revert(FIXED, DEFECTIVE, part)
    Q.judge_part(tree, "mod.py", FIXED, mutant, tokens, _seeds(), FIXED)
    assert not (tree / Q.PIN_TEST_NAME).exists()
    assert (tree / "mod.py").read_text(encoding="utf-8") == DEFECTIVE
