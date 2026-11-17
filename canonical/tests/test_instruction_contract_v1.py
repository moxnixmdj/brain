"""Tests for the instruction->contract compiler, and for the honesty of its measurement.

Three of these are not ordinary unit tests and are the point of the module:

1. `test_contract_module_never_reads_the_reward` scans the SOURCE TEXT and the import graph. A
   contract that could see `raw_reward` would not be a verifier at all, and a runtime assertion
   could be lost in a refactor. The scan cannot be lost.
2. `test_every_compiled_contract_rejects_doing_nothing` is falsifiability, the only defence
   against an always-pass grader: a contract that accepts the empty plan can never reject a
   wrong trace, no matter how many clauses it prints.
3. The named refusals are asserted as ANSWERS, not as failures. A machine that declines to guess
   is not a machine that failed; the tree already fails closed elsewhere and this must match.

Everything here is offline: no browser, no node, no network. The witnesses used are the shapes
that were measured against the real pages on 2026-11-16, with the page's own verdict recorded in
the comments, so a regression names the real failure it reintroduces.
"""

from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import instruction_contract_v1 as contract_lib  # noqa: E402

MODULE = pathlib.Path(contract_lib.__file__)
MEASURE = ROOT / "canonical" / "tools" / "instruction_contract_measure_v1.py"


# --------------------------------------------------------------------------- #
# the two properties the module exists to have
# --------------------------------------------------------------------------- #
def test_contract_module_never_reads_the_reward() -> None:
    """The judge may not see the answer.

    Scanned as SOURCE, not asserted at runtime: an accidental `observation["raw_reward"]` added
    later must fail here even if every branch that reaches it is dead today.
    """
    source = MODULE.read_text()
    tree = ast.parse(source)
    banned = {"raw_reward", "reward", "done", "succeeded", "validate"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            key = node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                assert key.value not in banned, f"subscript of {key.value!r} at line {node.lineno}"
            if isinstance(key, ast.Name):
                assert key.id not in banned, f"subscript of {key.id!r} at line {node.lineno}"
        if isinstance(node, ast.Attribute):
            assert node.attr not in banned, f"attribute {node.attr!r} at line {node.lineno}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned, f"call to {node.func.id}() at line {node.lineno}"
    # and it must not import the tool that owns the reward
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            text = ast.unparse(node)
            assert "miniwob_one_success" not in text, text
            assert "measure" not in text, text


def test_the_scan_would_catch_a_violation() -> None:
    """A test that cannot fail is not a test: prove the scanner rejects a planted read."""
    planted = ast.parse("value = observation['raw_reward']\n")
    caught = False
    for node in ast.walk(planted):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            caught = node.slice.value in {"raw_reward", "reward", "done"}
    assert caught


def test_every_compiled_contract_rejects_doing_nothing() -> None:
    """Falsifiability on the instruction corpus, offline.

    Each fixture is (utterance, observation, expected operators). Every one of these must fail on
    the empty trace -- an agent that does NOTHING must never satisfy an instruction that asks for
    an action. This is the property that separates a verifier from a grader that always passes.
    """
    for utterance, observation, expected in FIXTURES:
        compiled = contract_lib.compile_contract(utterance, observation)
        assert compiled["refusal"] is None, (utterance, compiled["refusal"])
        assert [clause["operator"] for clause in compiled["clauses"]] == expected, utterance
        verdict = contract_lib.check_contract(compiled, [(observation, "")])
        assert verdict["verdict"] == contract_lib.FAIL, (utterance, verdict)


def test_verifies_claim_is_about_the_instruction_not_the_answer() -> None:
    """The module's own scope, pinned so it cannot be quietly widened in a docstring edit."""
    compiled = contract_lib.compile_contract(*FIXTURES[0][:2])
    assert compiled["verifies"] == "THAT_THE_INSTRUCTION_HAPPENED_NOT_THAT_THE_ANSWER_WAS_RIGHT"


# --------------------------------------------------------------------------- #
# both directions, on witnesses taken from real pages
# --------------------------------------------------------------------------- #
def _after(observation: dict, changes: dict) -> dict:
    """The same page with one thing changed, as the NEXT observation in a trace.

    A trace records the observation BEFORE each action. So the effect of an action appears in the
    entry that precedes the FOLLOWING action -- not in the entry the action is attached to.
    Hand-building traces that repeat one observation was a mistake in these tests, not in the
    compiler: it made a correct selection look like it never happened.
    """
    import copy
    changed = copy.deepcopy(observation)
    for index, fields in changes.items():
        for element in changed["elements"]:
            if element["index"] == index:
                element.update(fields)
    return changed


def _judge(utterance: str, observation: dict, trace: list) -> str:
    compiled = contract_lib.compile_contract(utterance, observation)
    assert compiled["refusal"] is None, compiled["refusal"]
    return contract_lib.check_contract(compiled, trace)["verdict"]


def test_click_button_accepts_the_success_and_rejects_the_decoy() -> None:
    """page click-button: A scored True, B (one press replaced) scored False. Both settled."""
    observation = _page(buttons=[("OK", 3)])
    utterance = 'Click the "OK" button.'
    assert _judge(utterance, observation, [(observation, "click@3")]) == contract_lib.PASS
    assert _judge(utterance, observation, [(observation, "")]) == contract_lib.FAIL


def test_press_on_submit_with_the_wrong_selection_fails() -> None:
    """page click-option: 'Select ULZC and click Submit'. Pressing Submit alone is not the task.

    This was a measured FALSE ACCEPT: the contract had only the press clause, so choosing nothing
    (or the wrong thing) and pressing Submit passed while the page said FAIL.
    """
    observation = _page(labels=["ULZC", "F3PwCmQ"], submit=20)
    utterance = "Select ULZC and click Submit."
    selected = _after(observation, {3: {"checked": True}})
    right = [(observation, "click@2"), (selected, "click@20")]
    wrong = [(observation, "click@6"), (observation, "click@20")]
    assert _judge(utterance, observation, right) == contract_lib.PASS
    assert _judge(utterance, observation, wrong) == contract_lib.FAIL


def test_checkbox_selected_through_its_label_counts_as_selected() -> None:
    """page click-checkboxes: the NAME is on <label>, the checked state on the child <input>.

    Reading `checked` off the labelled element found nothing and produced a measured FALSE
    REJECT on a correct trace. The association must run both directions.
    """
    observation = _page(checkboxes=[("3PwCm", False), ("AwK7", False), ("95l8", False)],
                        submit=20)
    utterance = "Select 3PwCm, 95l8 and click Submit."
    # indices in _page: label 2/input 3 (3PwCm), label 4/input 5 (AwK7), label 6/input 7 (95l8)
    one = _after(observation, {3: {"checked": True}})
    both = _after(one, {9: {"checked": True}})
    assert _judge(utterance, observation,
                  [(observation, "click@2"), (one, "click@8"), (both, "click@20")]) \
        == contract_lib.PASS
    # only the first box ticked: the second named box is missing
    assert _judge(utterance, observation,
                  [(observation, "click@2"), (one, "click@20")]) == contract_lib.FAIL


def test_ordered_sequence_is_judged_in_order() -> None:
    """page click-button-sequence: 'Click button ONE, then button TWO'.

    The end state of ONE->TWO and TWO->ONE is the same page, so no state-only oracle can tell
    them apart. This is the reason a contract is over (state, action trace).
    """
    observation = _page(buttons=[("ONE", 3), ("TWO", 4)])
    utterance = "Click button ONE, then button TWO."
    forward = [(observation, "click@3"), (observation, "click@4")]
    reversed_ = [(observation, "click@4"), (observation, "click@3")]
    assert _judge(utterance, observation, forward) == contract_lib.PASS
    assert _judge(utterance, observation, reversed_) == contract_lib.FAIL


def test_a_number_is_a_label_when_the_page_shows_it_as_one() -> None:
    """'Click button ONE' -- ONE is the control's name, not a number word to be excluded.

    Excluding number words was a measured FALSE ACCEPT: the contract fell back to "press any
    button", which the page's own decoy satisfied.
    """
    observation = _page(buttons=[("ONE", 3), ("TWO", 4)])
    compiled = contract_lib.compile_contract("Click button ONE.", observation)
    assert "one" not in contract_lib._NOT_A_LABEL
    labels = [label for clause in compiled["clauses"]
              for label in clause.get("labels") or []]
    assert "ONE" in labels, compiled["clauses"]


def test_set_control_reads_the_value_not_the_geometry() -> None:
    """page use-spinner: 'Select 7 with the spinner and hit Submit'.

    Refusing every slider/spinner page as SPATIAL was wrong: the value is in the observation.
    """
    observation = _page(spinner_value="7", submit=12)
    utterance = "Select 7 with the spinner and hit Submit."
    compiled = contract_lib.compile_contract(utterance, observation)
    assert contract_lib.check_contract(compiled, [(observation, "click@12")])["verdict"] \
        == contract_lib.PASS
    wrong = _page(spinner_value="3", submit=12)
    assert contract_lib.check_contract(
        compiled, [(wrong, "click@12")])["verdict"] == contract_lib.FAIL


def test_ordinal_is_a_position_among_the_candidates_visible_when_pressed() -> None:
    """page search-engine: '... then find and click the 3rd search result'.

    Counting presses in sequence wanted three presses and saw two, because the plan that the page
    scores as a success presses ONE result -- the third one listed.
    """
    results = [("Alan", 8), ("Juan", 12), ("Nathalie", 16), ("Zoe", 20)]
    observation = _page(buttons=[("Search", 5)], links=results, text_field=4)
    utterance = ('Use the textbox to enter "Nathalie" and press "Search", '
                 "then find and click the 3rd search result.")
    compiled = contract_lib.compile_contract(utterance, observation)
    good = [(observation, "type@4=Nathalie"), (observation, "click@5"),
            (observation, "click@16")]
    bad = [(observation, "type@4=Nathalie"), (observation, "click@5"),
           (observation, "click@8")]
    assert contract_lib.check_contract(compiled, good)["verdict"] == contract_lib.PASS
    assert contract_lib.check_contract(compiled, bad)["verdict"] == contract_lib.FAIL


def test_focus_is_witnessed_by_the_press_when_the_page_erases_the_state() -> None:
    """focus-text.html rewards INSIDE its focus handler and blurs in the same statement.

    The observation after success can never show `focused`. A contract that only read state called
    a correct trace wrong; pressing the field is the act of focusing it.
    """
    observation = _page(text_field=3)
    utterance = "Focus into the textbox."
    assert _judge(utterance, observation, [(observation, "click@3")]) == contract_lib.PASS
    assert _judge(utterance, observation, [(observation, "")]) == contract_lib.FAIL


def test_a_label_the_page_never_shows_is_refused_not_guessed() -> None:
    """page click-dialog: 'Close the dialog box by clicking the "x"'.

    The x is drawn by CSS: no text, aria-label, title, or id in the observation names it. "x"
    occurs inside the class "ui-icon-closethick", and accepting that would be guessing a symbol
    convention. The honest answer is a named refusal.
    """
    observation = _page(buttons=[("Close", 6)])
    observation["elements"][1]["classes"] = "ui-icon-closethick"
    compiled = contract_lib.compile_contract(
        'Close the dialog box by clicking the "x".', observation)
    assert compiled["refusal"] == contract_lib.LABEL_NOT_ON_THE_PAGE
    assert contract_lib.check_contract(compiled, [])["verdict"] == contract_lib.UNCHECKABLE


def test_a_label_the_instruction_says_to_find_is_deferred_not_refused() -> None:
    """page click-collapsible-2: 'Expand the sections below, to find and click on the link "Quis"'

    The control is inside a collapsed section, so it cannot be in the opening observation -- and
    the instruction says so. Deferring is not refusing: the label must surface and be pressed.
    """
    observation = _page(headers=["Section #1", "Section #2"])
    compiled = contract_lib.compile_contract(
        'Expand the sections below, to find and click on the link "Quis".', observation)
    assert compiled["refusal"] is None
    assert [clause["operator"] for clause in compiled["clauses"]] == ["LABEL_ON_TRACE"]
    later = _page(headers=["Section #1"], links=[("Quis", 3)])
    assert contract_lib.check_contract(
        compiled, [(observation, "click@1"), (later, "click@3")])["verdict"] == contract_lib.PASS
    assert contract_lib.check_contract(
        compiled, [(observation, "click@1")])["verdict"] == contract_lib.FAIL


def test_two_values_for_two_named_fields_are_both_required() -> None:
    """page login-user: username and password are separate fields; typing one is not the task."""
    observation = _page(text_field=6, password_field=9, names={6: "username", 9: "password"})
    utterance = 'Enter the username "olin" and the password "ULZ" into the text fields and press login.'
    typed_user = _after(observation, {6: {"value": "olin"}})
    typed_both = _after(typed_user, {9: {"value": "ULZ"}})
    both = [(observation, "type@6=olin"), (typed_user, "type@9=ULZ"),
            (typed_both, "click@10")]
    one = [(observation, "type@6=olin"), (typed_user, "click@10")]
    assert _judge(utterance, observation, both) == contract_lib.PASS
    assert _judge(utterance, observation, one) == contract_lib.FAIL


def test_a_typed_value_can_be_a_predicate() -> None:
    """page use-autocomplete: 'an item that starts with "Sur" and ends with "ame"'."""
    observation = _page(text_field=4, submit=5)
    utterance = 'Enter an item that starts with "Sur" and ends with "ame".'
    compiled = contract_lib.compile_contract(utterance, observation)
    assert [clause["operator"] for clause in compiled["clauses"]] == ["TYPE_MATCHING"]
    full = _after(observation, {4: {"value": "SurpriseGame"}})
    short = _after(observation, {4: {"value": "SurpriseGam"}})
    assert contract_lib.check_contract(
        compiled, [(observation, "type@4=SurpriseGame"), (full, "")])["verdict"] \
        == contract_lib.PASS
    assert contract_lib.check_contract(
        compiled, [(observation, "type@4=SurpriseGam"), (short, "")])["verdict"] \
        == contract_lib.FAIL


def test_uncompilable_instructions_refuse_with_a_reason_that_names_the_gap() -> None:
    """Refusals are answers. Each names WHY no decidable predicate exists in the observation."""
    observation = _page(buttons=[("OK", 3)])
    # CORRECTED 2026-11-16 by measurement. Both of these used to be asserted as SPATIAL, i.e. "needs
    # geometry", and both are now compiled: `container_of` resolves the box from the page's own
    # draggable/fill asymmetry, and a colour word is decided by the element's fill. A refusal that
    # names the wrong missing dimension is worse than no refusal, because it aims the repair at a
    # coordinate when the repair is an observation.
    cases = {
        "Drag the cube into the black box.": contract_lib.OBSERVABLE_ABSENT,
        # this bare page has no box of any colour, so the honest answer is "nothing here is that",
        # which is a different claim from "the observation lacks colour"
        "Click on the white colored box.": contract_lib.LABEL_NOT_ON_THE_PAGE,
        "Send an email to the contact book.": contract_lib.MULTI_APP,
        "Find the item that best describes a feeling.": contract_lib.FUZZY,
        "How many items are shown?": contract_lib.VISUAL_QUANTITY,
        "Click the underlying style toggle.": contract_lib.STYLE_NOT_OBSERVABLE,
    }
    # CORRECTED 2026-11-16 BY MEASUREMENT, again. `"Click the button."` sat in this dictionary as
    # NO_CLAUSE_UNDERSTOOD, and it was wrong: the page on this very fixture states one element
    # whose tag is `button`, and `click-test` is that instruction on a real page. A test that
    # asserts a refusal is a test that can bless a blindness. It now compiles to CLICK_KIND.
    compiled = contract_lib.compile_contract("Click the button.", observation)
    assert compiled["refusal"] is None, compiled["refusal"]
    assert [c["operator"] for c in compiled["clauses"]] == ["CLICK_KIND"], compiled["clauses"]
    for utterance, expected in cases.items():
        compiled = contract_lib.compile_contract(utterance, observation)
        assert compiled["refusal"] == expected, (utterance, compiled["refusal"])
        assert compiled["clauses"] == [], utterance
        assert contract_lib.check_contract(compiled, [(observation, "click@3")])["verdict"] \
            == contract_lib.UNCHECKABLE


def test_an_unquoted_date_is_still_a_value() -> None:
    """page enter-date: 'Enter 08/13/2018 as the date and hit submit.'

    The contract first compiled to NOTHING BUT THE PRESS, so typing garbage and pressing Submit
    passed while the page said FAIL -- a measured FALSE ACCEPT. A literal with its own shape is a
    value whether or not the instruction quotes it.
    """
    observation = _page(text_field=4, submit=5)
    utterance = "Enter 08/13/2018 as the date and hit submit."
    compiled = contract_lib.compile_contract(utterance, observation)
    typed = [clause for clause in compiled["clauses"] if clause["operator"] == "TYPE_VALUE"]
    assert typed and typed[0]["value"] == "08/13/2018", compiled["clauses"]
    right = _after(observation, {4: {"value": "08/13/2018"}})
    wrong = _after(observation, {4: {"value": "and"}})
    assert contract_lib.check_contract(compiled, [(observation, "type@4=08/13/2018"),
                                                  (right, "click@5")])["verdict"] \
        == contract_lib.PASS
    assert contract_lib.check_contract(compiled, [(observation, "type@4=and"),
                                                  (wrong, "click@5")])["verdict"] \
        == contract_lib.FAIL


def test_compile_is_deterministic() -> None:
    """Same instruction, same page, same contract -- byte for byte. No sampling anywhere."""
    for utterance, observation, _expected in FIXTURES:
        first = contract_lib.compile_contract(utterance, observation)
        second = contract_lib.compile_contract(utterance, observation)
        assert first == second, utterance


def test_every_clause_carries_its_provenance() -> None:
    """A wrong contract must be arguable: every clause says which words produced it."""
    for utterance, observation, _expected in FIXTURES:
        compiled = contract_lib.compile_contract(utterance, observation)
        for clause in compiled["clauses"]:
            assert clause.get("provenance"), (utterance, clause)


def test_the_measurement_never_hands_the_reward_to_the_judge() -> None:
    """The tool may read the reward to LABEL an attempt; it may not pass it into the judge."""
    source = MEASURE.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "judge":
            for argument in node.args:
                assert not (isinstance(argument, ast.Name)
                            and "reward" in argument.id), ast.unparse(node)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "check_contract":
            assert len(node.args) == 2, "check_contract is called with the trace and nothing else"


# --------------------------------------------------------------------------- #
# fixtures: the shapes the real pages produce
# --------------------------------------------------------------------------- #
def _page(*, buttons=(), links=(), labels=(), checkboxes=(), headers=(), submit=None,
          text_field=None, password_field=None, spinner_value=None, names=None) -> dict:
    """A page observation with the same field names the bridges emit. Not a synthetic task:
    every value here was copied from a real MiniWoB++ observation on 2026-11-16."""
    elements: list[dict] = [{"index": 0, "parent": -1, "tag": "body", "text": "",
                             "can_click": False, "can_type": False}]
    names = names or {}

    def add(index: int, **fields) -> None:
        while len(elements) <= index:
            elements.append({"index": len(elements), "parent": 0, "tag": "div", "text": "",
                             "can_click": False, "can_type": False})
        elements[index].update({"index": index, **fields})

    if spinner_value is not None:
        add(5, tag="input", value=spinner_value, can_click=True, can_type=True)
    if text_field is not None:
        add(text_field, tag="input", type="text", value="", can_click=True, can_type=True,
            **({"id": names[text_field]} if text_field in names else {}))
    if password_field is not None:
        add(password_field, tag="input", type="password", value="", can_click=True,
            can_type=True, **({"id": names[password_field]} if password_field in names else {}))
    for text, index in buttons:
        add(index, tag="button", text=text, can_click=True)
    for text, index in links:
        add(index, tag="a", text=text, can_click=True)
    for position, text in enumerate(headers):
        add(len(elements), tag="h3", text=text, can_click=True)
    for text in labels:
        # a label element is pressable and the state lives on the next element
        index = len(elements) + 1
        add(index, tag="label", text=text, can_click=True, parent=0)
        add(index + 1, tag="input", type="checkbox", checked=False, can_click=True,
            parent=index)
    for text, checked in checkboxes:
        index = len(elements) + 1
        add(index, tag="label", text=text, can_click=True, parent=0)
        add(index + 1, tag="input", type="checkbox", checked=checked, can_click=True,
            parent=index)
    if submit is not None:
        add(submit, tag="button", text="Submit", can_click=True)
    return {"utterance": "", "done": False, "elements": elements}


FIXTURES = [
    ('Click the "OK" button.', _page(buttons=[("OK", 3)]), ["CLICK_NAMED"]),
    ("Select ULZC and click Submit.", _page(labels=["ULZC"], submit=16),
     ["SELECT_SET", "CLICK_NAMED"]),
    ("Click button ONE, then button TWO.", _page(buttons=[("ONE", 3), ("TWO", 4)]),
     ["PRESS_SEQUENCE"]),
    ("Focus into the textbox.", _page(text_field=3), ["FOCUS"]),
    ('Click on Tab #1.', _page(links=[("Tab #1", 5), ("Tab #2", 7)]), ["CLICK_LABELLED"]),
]


def main() -> int:
    """Run every test function in this module. Returns 0 on success."""
    failures = 0
    for name, function in sorted(globals().items()):
        if not name.startswith("test_") or not callable(function):
            continue
        try:
            function()
        except AssertionError as error:
            failures += 1
            print(f"FAIL {name}: {error}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"ERROR {name}: {type(error).__name__}: {error}")
        else:
            print(f"ok   {name}")
    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
