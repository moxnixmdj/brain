"""r92 -- ground a goal by SEARCHING THE PAGE, not by parsing the sentence.

Four bugs, each of which made the module look like a system limitation:

  1. MiniWob renders the goal onto the page, so the longest page string mentioned in the
     goal was THE GOAL ITSELF.
  2. The fix for (1) removed any page string appearing in the goal -- which is exactly the
     target. 'Tab #1' was on the page and in the goal and got deleted.
  3. Boilerplate names were deleted rather than ranked, so ONE/TWO vanished.
  4. 'Submit' appears in nearly every goal and was the longest match, so it won every tie.
  5. (not yet fixed) the DOM query discarded every <option>, so a dropdown saw only Submit.

The lesson is the inversion, not the fixes: the goal is underspecified language, the page
is fully specified data, so the operation is an intersection, not a parse.
"""
from canonical.runtime.page_first_grounding_v1 import ground


def test_it_finds_a_target_that_is_on_the_page_and_in_the_goal():
    r = ground("Click on Tab #1.", ["Tab #1", "Tab #2", "Tab #3"])
    assert r["status"] == "GROUNDED"
    assert r["target"] == "Tab #1"


def test_the_rendered_goal_never_grounds_to_itself():
    goal = "Click on the numbers in ascending order."
    r = ground(goal, [goal, "1", "2", "3"])
    assert r["target"] != goal


def test_submit_does_not_beat_a_real_target():
    """'and click Submit' is in nearly every goal; it must never win."""
    r = ground("Select Germany from the list and click Submit.",
               ["Germany", "France", "Submit"])
    assert r["target"] == "Germany"


def test_two_equally_specific_candidates_are_refused():
    r = ground("Click button ONE, then click button TWO.", ["ONE", "TWO"])
    assert r["status"] == "AMBIGUOUS"
    assert r["target"] is None


def test_nothing_mentioned_is_reported_not_guessed():
    r = ground("Click the button.", ["Submit", "Cancel"])
    assert r["status"] in ("NOT_MENTIONED", "AMBIGUOUS")


def test_a_longer_specific_string_outranks_a_short_one():
    r = ground("Book the flight from El Paso to JHM.", ["El Paso", "JHM", "Submit"])
    assert r["target"] == "El Paso"
