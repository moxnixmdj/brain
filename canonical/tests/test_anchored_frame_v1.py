"""The frame: can the machine name the REGION of the page a word picks out, and prove when it cannot?

Every observation in `fixtures/real_observations_20261116_frames_v1.json` was captured by this
project's own chromium bridge against `Farama-Foundation/miniwob-plusplus` at seed 1060 on
2026-11-16. None of it is synthetic; the boxes, classes and words are what the pages reported.

Why this file exists
--------------------
For three rounds the compiler refused the email and contacts pages with
`REFUSED__MULTI_APP_STATE_OUTSIDE_OBSERVATION` -- "the state lives outside the observation". The
dumps said otherwise every time: `email-sender 'Enrichetta'`, the subject, the body, and
`div.email-actions` holding `span.trash` and `span.star` were all in the observation. What the
machine could not do was NAME THE ROW. It could list 107 elements and it could not say "that one,
and the trash inside it". `MULTI_APP` was a true statement about the vocabulary, not about the
world, and aiming engineering at the world cost two rounds.

So the load-bearing assertions here are not "the function runs". They are:

  * the frame is the LARGEST region that does not swallow a second record -- on `email-inbox` the
    nearest container holding a control is `email-left`, which holds the sender, subject and body,
    while the star is in the SIBLING `email-right`; stopping at the nearest one located the email
    and then could not find the control in the same row;
  * a control is named by its OWN text or an EXACT class token, never a prefix (`email-sender`
    starts with `email` and is not a control);
  * what the page cannot show is reported as ABSENT / NOT ON SCREEN, by name, and a record that is
    one page-turn away is a SEARCH to run, not a missing observable (`phone-book`);
  * the whole sentence survives the frame: the frame answers WHICH RECORD, and the quoted text is
    still a value to write.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import anchored_frame_v1 as frame  # noqa: E402
from canonical.runtime import instruction_contract_v1 as contract  # noqa: E402
from canonical.runtime import instruction_policy_v1 as policy  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "real_observations_20261116_frames_v1.json"


def _pages() -> dict:
    return json.loads(FIXTURES.read_text())


def _obs(page: str, where: str = "observation") -> dict:
    """The observation for one page at one moment, WITH the instruction on it.

    An observation without its utterance is not an observation: the arm's only input is the pair,
    and a fixture that separated them silently handed the policy an empty instruction.
    """
    page_data = _pages()[page]
    observation = dict(page_data[where])
    observation["utterance"] = page_data["utterance"]
    return observation


# --------------------------------------------------------------------------- #
# the frame names the record, and the record is not the nearest container
# --------------------------------------------------------------------------- #
def test_the_frame_is_the_row_and_not_the_half_of_it() -> None:
    """`email-inbox`: the star is in `email-right`, the name in `email-left`. One record."""
    observation = _obs("email-inbox")
    found = frame.find_frame("Enrichetta", observation, controls=["star"])
    assert found.outcome == frame.RESOLVED, found.outcome
    inside = frame._descendants({int(e["index"]): e for e in observation["elements"]},
                                frame._children(observation["elements"]), found.container)
    classes = {str(observation["elements"][i].get("classes")) for i in inside}
    assert {"email-left", "email-right"} <= classes, classes
    # and the control it names is inside that same region
    star = [c for c in found.controls if c["word"] == "star"]
    assert star and star[0]["index"] in inside


def test_a_control_is_never_a_class_prefix() -> None:
    """`email-sender` starts with `email`; it is not a control. `trash` and `star` are."""
    observation = _obs("email-inbox")
    found = frame.find_frame("Enrichetta", observation, controls=["email", "trash", "star"])
    pressed = {c["word"] for c in found.controls}
    assert "email" not in pressed, pressed
    assert {"trash", "star"} <= pressed, pressed


def test_the_frame_does_not_swallow_the_next_record() -> None:
    """The region must stop before a different sender: Peggi and Jolynn are other records."""
    observation = _obs("email-inbox")
    found = frame.find_frame("Enrichetta", observation, controls=["star"])
    by_index = {int(e["index"]): e for e in observation["elements"]}
    inside = frame._descendants(by_index, frame._children(observation["elements"]),
                                found.container)
    names = {str(by_index[i].get("text")) for i in inside if "email-sender" in
             str(by_index[i].get("classes"))}
    assert "Enrichetta" in names
    assert "Peggi" not in names and "Jolynn" not in names, names


# --------------------------------------------------------------------------- #
# what the page does not show, said by name
# --------------------------------------------------------------------------- #
def test_a_record_that_is_not_on_screen_is_a_search_not_a_missing_observable() -> None:
    """`phone-book`: Larissa is not shown, and the page offers a way to reach her."""
    observation = _obs("phone-book")
    found = frame.find_frame("Larissa", observation, controls=["email"])
    assert found.outcome == frame.NO_RECORD, found.outcome
    assert found.reachable_by, "the pager is on the page; the record is one step away"


def test_a_control_the_record_does_not_hold_is_named_absent() -> None:
    """Asking a record for a control it does not contain is not a licence to press anything."""
    observation = _obs("email-inbox-important")
    result = frame.control_of("Enrichetta", "reply", observation)
    assert result["outcome"] == frame.ABSENT, result


# --------------------------------------------------------------------------- #
# the whole sentence survives the frame
# --------------------------------------------------------------------------- #
def test_the_typed_text_is_not_swallowed_by_the_frame() -> None:
    """`reply ... with the text "X"`: the frame answers WHICH, the quote is still a value."""
    compiled = contract.compile_contract(_pages()["email-inbox-reply"]["utterance"],
                                         _obs("email-inbox-reply"))
    assert compiled["refusal"] is None
    operators = [clause["operator"] for clause in compiled["clauses"]]
    assert "OPEN_THEN_CLICK" in operators, operators
    assert compiled["wants_text"] is True


def test_the_arm_opens_the_record_then_finds_the_control_inside_it() -> None:
    """One language for two steps: open the frame, then press the control it now holds."""
    after_open = _obs("email-inbox", "after_opening_the_record")
    found = frame.find_frame("Enrichetta", after_open, controls=["reply"])
    assert found.outcome == frame.RESOLVED, found.outcome
    reply = [c for c in found.controls if c["word"] == "reply" and c["can_click"]]
    assert reply, found.controls
    # the reply control is INSIDE the opened email -- not the page container, and not the
    # sender's name, which also sits inside the record
    by_index = {int(e["index"]): e for e in after_open["elements"]}
    classes = str(by_index[reply[0]["index"]].get("classes") or "")
    assert "email-sender" not in classes and "email-body" not in classes, classes


def test_a_named_record_with_no_reachable_control_compiles_to_opening_it() -> None:
    """When the control appears only after opening, the clause says so instead of guessing."""
    compiled = contract.compile_contract(_pages()["email-inbox-forward"]["utterance"],
                                         _obs("email-inbox-forward"))
    assert compiled["refusal"] is None
    assert [c["operator"] for c in compiled["clauses"]] == ["OPEN_THEN_CLICK"]


# --------------------------------------------------------------------------- #
# the refusal that was wrong for three rounds
# --------------------------------------------------------------------------- #
def test_the_email_pages_are_no_longer_refused_as_state_outside_the_observation() -> None:
    for page in ("email-inbox", "email-inbox-reply", "email-inbox-forward", "email-inbox-delete",
                 "email-inbox-important", "email-inbox-noscroll"):
        said = _pages()[page]["utterance"]
        compiled = contract.compile_contract(said, _obs(page))
        assert compiled.get("refusal") != contract.MULTI_APP, (page, compiled.get("refusal"))


def test_the_policy_turns_the_clause_into_an_action_with_no_reward_and_no_memory() -> None:
    observation = _obs("email-inbox-delete")
    arm = policy.ContractArm()
    arm.begin(observation, 1060)
    action = arm.next_action(observation)
    # the trash inside Enrichetta's row, found by the instruction alone -- element 15, which is
    # the FIRST thread's trash; 25 and 35 belong to Peggi and Jolynn and would be wrong
    assert action == "click@15", action


def main() -> int:
    tests = [(name, obj) for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"ok   {name}")
        except Exception as error:                                   # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {error}")
    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
