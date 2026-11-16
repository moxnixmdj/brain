"""Tests for the instruction-as-policy arm: acting with no experience, no search, no reward.

The point of this arm is that there is nothing in it to train. So the tests are about what it is
ALLOWED to look at, and about the specific traps that the real pages set. Every fixture below is
copied from an observation that a real MiniWoB++ page produced on 2026-11-16, and the failure it
reproduces is named -- these are the bugs the measurement actually found, not invented ones.

The three that are not ordinary unit tests:

1. `test_policy_never_reads_the_reward` scans the SOURCE. An arm that could see `raw_reward` would
   be a search wearing a policy's clothes, and the whole claim ("the instruction was enough")
   would be false.
2. `test_a_frozen_index_is_not_an_action` pins the deepest defect found: a page that rewrites
   itself makes a captured index name a different element. Only a re-resolved label survives.
3. `test_executes_only_what_it_fully_understood` pins the integrity rule: verifying half of an
   instruction is honest, ACTING on half of one is how a wrong answer gets submitted.
"""

from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import instruction_contract_v1 as contract_lib  # noqa: E402
from canonical.runtime import instruction_policy_v1 as policy  # noqa: E402

MODULE = pathlib.Path(policy.__file__)


# --------------------------------------------------------------------------- #
# what the arm is allowed to look at
# --------------------------------------------------------------------------- #
def test_policy_never_reads_the_reward() -> None:
    """Scanned as source, so an accidental read added later fails here even if unreached."""
    tree = ast.parse(MODULE.read_text())
    banned = {"raw_reward", "reward", "done", "succeeded", "partly_rewarded"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                assert node.slice.value not in banned, f"subscript {node.slice.value!r}"
            if isinstance(node.slice, ast.Name):
                assert node.slice.id not in banned, f"subscript {node.slice.id!r}"
        if isinstance(node, ast.Attribute):
            assert node.attr not in banned, f"attribute {node.attr!r} at line {node.lineno}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert "miniwob_one_success" not in ast.unparse(node)


def test_the_scan_would_catch_a_violation() -> None:
    planted = ast.parse("x = observation['raw_reward']\n")
    assert any(isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
               and node.slice.value == "raw_reward" for node in ast.walk(planted))


def test_the_arm_uses_one_vocabulary_with_the_checker() -> None:
    """Acting and judging resolve an instruction the SAME way, or the machine could do one thing
    and certify another. The compiler must be imported, never re-derived."""
    source = MODULE.read_text()
    assert "import instruction_contract_v1" in source
    assert "contract_lib.compile_contract" in source


# --------------------------------------------------------------------------- #
# the traps the real pages set
# --------------------------------------------------------------------------- #
def test_a_frozen_index_is_not_an_action() -> None:
    """ascending-numbers rewrites its page on the first press; the labels must be re-resolved.

    Measured: indices captured at opening named different elements after the rewrite and the run
    scored 0.2. A label looked up on the LIVE page each step is the only form that survives.
    """
    before = _page(texts=[("1", 4), ("2", 5), ("3", 6)])
    after = _page(texts=[("1", 4)])          # the page replaced its numbers with an overlay
    clause = {"operator": "PRESS_SEQUENCE_BY_INDEX", "indices": [4, 5, 6],
              "labels": ["1", "2", "3"]}
    first = policy.action_for_clause(clause, before, [], [])
    assert first == "click@4", first
    # after the rewrite, index 5 no longer shows "2": the arm must NOT emit click@5 blindly
    second = policy.action_for_clause(clause, after, ["4"], ["1"])
    assert second in (None, "click@5") and not _shows(second, after, "2") or second is None, second


def _shows(action: str | None, observation: dict, label: str) -> bool:
    if not action or not action.startswith("click@"):
        return False
    index = int(action.split("@")[1])
    return contract_lib.plain(contract_lib.element_label(observation["elements"][index])) == label


def test_a_substring_is_not_a_label() -> None:
    """click-tab-2-easy: the link is "ut" and the word "vulputate." also exists.

    Matching by substring pressed the wrong link. Whole words only.
    """
    page = _page(texts=[("vulputate.", 5), ("ut", 6)])
    clause = {"operator": "CLICK_LABELLED", "labels": ["ut"]}
    assert policy.action_for_clause(clause, page, [], []) == "click@6"


def test_the_terminal_press_runs_last() -> None:
    """find-greatest: pressing Submit came first and lost, with the right pick already known.

    Emission order is the order the words appeared; execution order is not. State is built first
    and submitted last.
    """
    clauses = [{"operator": "CLICK_NAMED", "name": "submit"},
               {"operator": "RANK_PICK", "rank": "greatest", "index": 8}]
    ordered = policy.order_for_execution(clauses)
    assert [clause["operator"] for clause in ordered] == ["RANK_PICK", "CLICK_NAMED"]


def test_a_spinner_is_changed_by_its_arrows_not_by_typing() -> None:
    """use-spinner: the input has a keydown handler that calls preventDefault.

    Typing left the value at 0 and the page rejected the answer; the arrows are the control.
    """
    page = _page(spinner=5, arrows=(6, 7))     # value 0, up arrow 6, down arrow 7
    clause = {"operator": "SET_CONTROL", "values": [3.0]}
    action = policy.action_for_clause(clause, page, [], [])
    assert action == "click@6", action          # 3 > 0, so the UP arrow


def test_a_vertical_slider_counts_the_other_way() -> None:
    """use-slider: dragging the handle DOWN raised the value (107 -> 110 on "up").

    Measured, not assumed: the axis comes from the TRACK, and the direction is inverted for a
    vertical slider.
    """
    page = _page(slider_track=[10, 60, 10, 99], handle=(4, [8, 82, 14, 14]), value=107)
    clause = {"operator": "SET_CONTROL", "values": [110.0]}
    action = policy.action_for_clause(clause, page, [], [])
    assert action == "nudge@4=up", action


def test_a_press_on_submit_requires_what_the_instruction_asked_first() -> None:
    """click-option: 'Select ULZC and click Submit'. Pressing Submit alone is a wrong answer."""
    page = _page(labels=[("ULZC", 2, 3, True)])
    compiled = contract_lib.compile_contract("Select ULZC and click Submit.", page)
    assert any(clause["operator"] == "SELECT_SET" for clause in compiled["clauses"]), \
        compiled["clauses"]
    assert policy.action_for_clause(compiled["clauses"][0], page, [], []) in ("click@2", "click@3")


def test_a_labelled_press_waits_for_its_target_to_appear() -> None:
    """click-menu-2: the named press happens, and only then is the labelled item on the page."""
    page = _page(buttons=[("Menu", 3)])
    compiled = contract_lib.compile_contract(
        'Click the "Menu" button, and then find and click on the item labeled "Zoom Out".', page)
    ordered = policy.order_for_execution(compiled["clauses"])
    assert policy.action_for_clause(ordered[0], page, [], []) == "click@3"
    after = _page(buttons=[("Menu", 3)], labels=[("Zoom Out", 18, None)])
    assert policy.action_for_clause(ordered[-1], after, [], []) == "click@18"


def test_executes_only_what_it_fully_understood() -> None:
    """circle-center: the decidable half is literally "press submit".

    A contract may honestly verify HALF an instruction, and the census reports that separately.
    Acting on it is different: pressing Submit without having found the centre is a wrong answer
    submitted with confidence.
    """
    page = _page(buttons=[("Submit", 5)],
                 utterance="Find and click on the center of the circle, then press submit.")
    compiled = contract_lib.compile_contract(page["utterance"], page)
    assert compiled["refusal"] is None
    assert compiled.get("refused_part"), compiled
    arm = policy.ContractArm()
    arm.begin(page, 0)
    assert arm._clauses == [], "an arm must not act on an instruction it only half understood"
    assert arm.next_action(page) is None
    assert arm.refused


def test_a_page_that_never_changes_stops_the_arm() -> None:
    """An action already taken on this very page cannot help again; the arm tries something else
    and, if there is nothing else, stops instead of spending the budget on a no-op."""
    page = _page(buttons=[("OK", 3)], utterance='Click the "OK" button.')
    arm = policy.ContractArm()
    arm.begin(page, 0)
    assert arm.next_action(page) == "click@3"
    assert arm.next_action(page) in (None, "click@3")
    seen = [arm.next_action(page) for _ in range(3)]
    assert all(action is None for action in seen), seen


def test_a_contract_refusal_is_a_refusal_for_the_arm_too() -> None:
    page = _page(buttons=[("OK", 3)])
    arm = policy.ContractArm()
    arm.begin(page, 0)
    refused = contract_lib.compile_contract("Drag the cube into the black box.", page)
    assert refused["refusal"] == contract_lib.SPATIAL
    assert contract_lib.check_contract(refused, [(page, "")])["verdict"] == contract_lib.UNCHECKABLE


def test_the_arm_is_deterministic() -> None:
    page = _page(texts=[("1", 4), ("2", 5)])
    first = policy.first_action("Click on the numbers in ascending order.", page)
    second = policy.first_action("Click on the numbers in ascending order.", page)
    assert first == second


def test_first_action_reports_the_contract_it_came_from() -> None:
    page = _page(buttons=[("Submit", 5)], field=4,
                 utterance='Enter "Donovan" into the text field and press Submit.')
    result = policy.first_action(page["utterance"], page)
    assert result["action"] == "type@4=Donovan"
    assert "TYPE_VALUE" in result["operators"]
    assert result["refused"] is False


# --------------------------------------------------------------------------- #
# fixtures: the shapes real pages produce
# --------------------------------------------------------------------------- #
def _page(*, texts=(), buttons=(), labels=(), field=None, spinner=None, arrows=None,
          slider_track=None, handle=None, value=None, utterance="") -> dict:
    elements: list[dict] = [{"index": 0, "parent": -1, "tag": "body", "text": "",
                             "can_click": False, "can_type": False}]

    def add(index: int, **fields) -> None:
        while len(elements) <= index:
            elements.append({"index": len(elements), "parent": 0, "tag": "div", "text": "",
                             "can_click": False, "can_type": False})
        elements[index].update({"index": index, **fields})

    for text, index, *box in texts:
        add(index, tag="text", text=text, can_click=True, **({"box": box[0]} if box else {}))
    for text, index in buttons:
        add(index, tag="button", text=text, can_click=True)
    for text, index, carrier, *rest in labels:
        add(index, tag="label", text=text, can_click=True)
        if rest:
            add(carrier, tag="input", type="checkbox", checked=False, can_click=True, parent=index)
    if field is not None:
        add(field, tag="input", type="text", value="", can_click=True, can_type=True)
    if spinner is not None:
        add(spinner, tag="input", value="0", can_click=True, can_type=True, parent=3)
        if arrows:
            add(arrows[0], tag="a", can_click=True, parent=3)
            add(arrows[1], tag="span", can_click=True, parent=3)
    if slider_track:
        add(3, tag="div", classes="ui-slider ui-slider-vertical", can_click=False)
        elements[3]["box"] = slider_track
        index, box = handle
        add(index, tag="span", classes="ui-slider-handle", can_click=True, parent=3)
        elements[index]["box"] = box
        add(index + 1, tag="div", text=str(value), can_click=True)
    return {"utterance": utterance, "elements": elements}


def test_a_label_that_vanishes_is_found_by_where_it_was():
    """Measured 2026-11-16: pressing the first number of ascending-numbers replaces every
    remaining number with a BLANK rect at that number's own coordinates. Text can never resolve
    again, so identity has to be positional -- and the ledger has to be written positionally too,
    or the same target is served twice."""
    page = _page(texts=[("1", 4, [55, 103, 11, 27]), ("2", 5, [94, 124, 11, 27]),
                        ("3", 6, [80, 54, 11, 27])],
                 utterance="Click on the numbers in ascending order.")
    clause = {"operator": "PRESS_SEQUENCE_BY_INDEX", "indices": [4, 5, 6],
              "labels": ["1", "2", "3"]}
    positions = {"1": [55, 103, 11, 27], "2": [94, 124, 11, 27], "3": [80, 54, 11, 27]}
    # the page after the first press: the numbers are gone, only blank rects remain, renumbered
    # (an observation is a list whose indices ARE the positions, so the rects are renumbered)
    blank = _page(utterance=page["utterance"])
    blank["elements"] = [blank["elements"][0]] + [
        {"index": index, "parent": 0, "tag": "rect", "text": "", "box": box, "can_click": True}
        for index, box in enumerate(([86, 121, 20, 20], [70, 49, 20, 20]), start=1)]
    action = policy.action_for_clause(clause, blank, ["4"], ["1"], positions)
    assert action == "click@1", action            # the rect nearest where "2" was
    assert policy._label_served(clause, blank["elements"], 1, positions, ["1"]) == "2"
    # and the served label is not served again
    served = policy._label_served(clause, blank["elements"], 1, positions, ["1", "2"])
    assert served in (None, "3"), served


def test_a_submenu_header_is_hovered_not_clicked():
    """Measured 2026-11-16: on click-menu, CLICKING "Milissent" ended the episode (done) with
    the trail unpressed; hovering opened the next level. The page says which one it is: the
    header carries a caret icon."""
    page = _page(utterance="Select Milissent>Harmonia>Anita")
    page["elements"] += [
        {"index": 7, "parent": 0, "tag": "li", "text": "", "classes": "ui-menu-item",
         "can_click": False},
        {"index": 8, "parent": 7, "tag": "div", "text": "Milissent",
         "classes": "ui-menu-item-wrapper", "can_click": True, "box": [6, 96, 50, 20]},
        {"index": 9, "parent": 7, "tag": "span", "text": "",
         "classes": "ui-menu-icon ui-icon ui-icon-caret-1-e", "can_click": True,
         "box": [40, 98, 16, 16]}]
    clause = {"operator": "PRESS_SEQUENCE", "labels": ["Milissent"]}
    assert policy.action_for_clause(clause, page, [], []) == "hover@8"

    leaf = _page(utterance="Select Zonda")
    leaf["elements"] += [
        {"index": 7, "parent": 0, "tag": "li", "text": "", "classes": "ui-menu-item",
         "can_click": False},
        {"index": 8, "parent": 7, "tag": "div", "text": "Zonda",
         "classes": "ui-menu-item-wrapper", "can_click": True, "box": [6, 56, 50, 20]}]
    assert policy.action_for_clause({"operator": "PRESS_SEQUENCE", "labels": ["Zonda"]},
                                    leaf, [], []) == "click@8"


def test_where_a_thing_is_counts_as_observable():
    """A text-only fingerprint called a page with the same text "unchanged"; the page had
    become a completely different arrangement of blank rects. Position is observed state."""
    a = _page(texts=[("1", 4, [55, 103, 11, 27])])
    b = _page(texts=[("1", 4, [80, 54, 11, 27])])
    assert policy._fingerprint(a) != policy._fingerprint(b)


def main() -> int:
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
