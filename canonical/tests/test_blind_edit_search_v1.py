"""The blind edit search, and the calibration that had to come before its result meant anything.

A negative result is only informative if the instrument is proven able to produce a positive. The calibration
here is the reason the main result can be read as "the mechanism is too weak" rather than "the tasks are hard".
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools import minimal_edit_search_v1 as search  # noqa: E402

RECEIPT = REPO / "canonical" / "corpus" / "blind_edit_search_20261124_V1.json"


def test_a_quantifier_inside_an_fstring_literal_is_found():
    """The AST round-trip version silently skipped every f-string. Raw text does not."""
    line = '        raise E(f\'bad "{value!r}" * here\')\n'
    candidates = search.quantifier_edits(pathlib.Path("p"), line)
    assert candidates
    # the edit must be a substitution inside the literal, not a no-op
    assert any(candidate["text"] != line for candidate in candidates)


def test_the_edit_forms_are_blind_to_domain_vocabulary():
    """No branch may test a domain word. Comments and docstrings may discuss them; code may not."""
    import ast as ast_module
    tree = ast_module.parse(pathlib.Path(search.__file__).read_text())
    compared: set[str] = set()
    for node in ast_module.walk(tree):
        if isinstance(node, ast_module.Constant) and isinstance(node.value, str):
            compared.add(node.value)
    for node in ast_module.walk(tree):
        if isinstance(node, ast_module.Compare):
            for part in [node.left, *node.comparators]:
                if isinstance(part, ast_module.Constant) and isinstance(part.value, str):
                    compared.add(part.value)
    code_strings = {value for value in compared if value.isidentifier() and len(value) > 4}
    for domain_word in ("licence", "license", "requirement", "marker", "regex"):
        assert domain_word not in code_strings, f"{domain_word} is branched on in code"


def test_there_is_no_per_task_rule_in_the_module():
    """The whole point was one mechanism instead of an operator per bug family."""
    source = pathlib.Path(search.__file__).read_text()
    assert "TEST_FIXTURE_TASKS" not in source


def test_the_receipt_records_zero_on_both_sets():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["measured"]["solved"] == 0
    assert receipt["calibration"]["solved"] == 0
    assert "weaker than the thing it replaces" in receipt["calibration"]["reading"]


def test_the_instrument_defects_are_recorded():
    receipt = json.loads(RECEIPT.read_text())
    defects = " ".join(receipt["what_went_wrong_along_the_way"])
    assert "f-string" in defects
    assert "interleav" in defects


def test_the_one_stable_result_is_still_stated():
    receipt = json.loads(RECEIPT.read_text())
    assert "17 of 28" in receipt["the_one_thing_that_has_held_for_seven_rounds"]
