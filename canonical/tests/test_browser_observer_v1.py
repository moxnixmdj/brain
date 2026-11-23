"""Tests for `browser_observer_v1` -- judging a page in its own words.

These are LIVE tests: they drive a real HeadlessChrome over CDP. A browser test that mocks the browser
tests the mock, and the whole point of this module is that a page must be asked rather than assumed.

Every test here skips cleanly when no browser is running, so a checkout without one is not a red suite --
but a checkout WITH one gets the real thing, which is the only version worth having.
"""
from __future__ import annotations

import http.server
import pathlib
import shutil
import socket
import tempfile
import threading

import pytest

from canonical.runtime import browser_observer_v1 as BO
from canonical.runtime import browser_v1

_PAGE = """<!doctype html><html><head><title>Records</title></head><body>
<h1>Record manager</h1>
<div id="status">none</div>
<form id="f">
  <label>Name <input id="name" placeholder="record name"></label>
  <label>Amount <input id="amount" placeholder="amount"></label>
  <button id="save" type="button">Save record</button>
  <button id="clear" type="button">Clear all</button>
</form>
<script>
document.getElementById('save').onclick = () => {
  const n = document.getElementById('name').value, a = document.getElementById('amount').value;
  document.getElementById('status').textContent = 'saved ' + n + ' = ' + a;
};
document.getElementById('clear').onclick = () => {
  document.getElementById('status').textContent = 'none';
};
</script></body></html>
"""


def _browser_ready() -> bool:
    try:
        return bool(browser_v1.running())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _browser_ready(),
                                reason="no Chromium on the CDP port")


@pytest.fixture(scope="module")
def page_url():
    """A page served on a free loopback port. Local HTTP needs no certificate pin, which is why a plain
    page is used: the pin applies to TLS and requiring it everywhere refused every local fixture."""
    directory = tempfile.mkdtemp(prefix="pages_")
    (pathlib.Path(directory) / "index.html").write_text(_PAGE)
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
        *args, directory=directory, **kwargs)
    handler.log_message = lambda *args, **kwargs: None
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d/" % port
    finally:
        server.shutdown()
        shutil.rmtree(directory, ignore_errors=True)


def test_the_page_reports_its_own_words_not_only_its_controls(page_url: str) -> None:
    """THE DEFECT THIS MODULE EXISTS FOR. The element index carries `a,button,input,textarea,select` -- so
    a `<div>` a handler writes into is invisible, and an act whose effect lands there looks like it did
    nothing. The page's rendered text is the sense a person uses and the only evidence an effect happened.
    """
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})
    seen = BO.observe(browser)

    assert seen["ok"] is True, seen
    assert seen["sense"] == "RENDERED_TEXT", seen["sense"]
    assert "Record manager" in seen["text"]
    assert "none" in seen["text"], seen["text"]        # a div, never in the element index
    assert any(e.get("tag") == "button" for e in seen["elements"])


def test_every_op_reports_PASS_and_the_effect_is_still_judged_present(page_url: str) -> None:
    """The live case, end to end: fill two fields, press Save, and read the result from the page."""
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})

    verdict = BO.judge(browser, [
        {"type": "FILL", "selector": "#name", "text": "alpha"},
        {"type": "FILL", "selector": "#amount", "text": "4"},
        {"type": "CLICK_TEXT", "text": "Save record"},
    ], "saved alpha = 4")

    assert verdict["judged"] is True, verdict
    assert verdict["ops_all_passed"] is True, verdict["operations"]
    assert verdict["verdict"] == "EFFECT_CONFIRMED", verdict


def test_PASS_is_not_evidence_and_an_absent_effect_is_reported_as_absent(page_url: str) -> None:
    """EVERY OPERATION SUCCEEDS AND THE PAGE IS UNCHANGED -- the failure mode a driver's return code cannot
    detect, and the reason `PASS` is reported but never trusted.

    Nothing is clicked that would write the expectation, so all ops pass and the verdict must be
    `EFFECT_ABSENT`. If this ever returns CONFIRMED, the judge is reading the driver rather than the page.
    """
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})

    verdict = BO.judge(browser, [
        {"type": "FILL", "selector": "#name", "text": "alpha"},
    ], "saved alpha = 4")

    assert verdict["ops_all_passed"] is True, verdict["operations"]
    assert verdict["verdict"] == "EFFECT_ABSENT", verdict


def test_an_effect_that_was_already_there_is_not_evidence(page_url: str) -> None:
    """A CONFIRMATION MUST DIFFER FROM THE STATE BEFORE THE ACT, or the act gets credit for a world it did
    not change. The first save leaves `saved alpha = 4` on the page; a second run must not confirm it again
    from the same words.
    """
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})
    first = BO.judge(browser, [
        {"type": "FILL", "selector": "#name", "text": "alpha"},
        {"type": "FILL", "selector": "#amount", "text": "4"},
        {"type": "CLICK_TEXT", "text": "Save record"},
    ], "saved alpha = 4")
    assert first["verdict"] == "EFFECT_CONFIRMED", first

    # the words are on the page already; doing nothing must not confirm them again
    second = BO.judge(browser, [], "saved alpha = 4")
    assert second["verdict"] == "THE_EFFECT_WAS_ALREADY_THERE", second


def test_the_completion_verification_gap_is_zero_on_cases_that_discriminate(page_url: str) -> None:
    """WebPageBench (arXiv 2609.35026, Sept 2026) measures the gap between what agents DECLARE finished and
    what the interface confirms: on their 152-task leaderboard it reaches **41 points**, and one
    configuration declares every task finished while satisfying the conditions on 59%.

    That gap exists because "the loop stopped" and "the world agrees" are different events. This test
    measures ours, on cases chosen to include the ways a page can look finished without being finished:
    a fill with no submit, a success followed by an undo, a wrong value, a missing field.

    RESULT: five of five agree, gap zero. The reason is structural rather than clever -- every stop but one
    is a refusal, so there is no path by which the loop says done without having read the words -- and the
    test exists so that a future change that reintroduces over-claiming fails HERE rather than on a
    leaderboard.
    """
    fill = [{"type": "FILL", "selector": "#name", "text": "alpha"},
            {"type": "FILL", "selector": "#amount", "text": "4"}]
    save = {"type": "CLICK_TEXT", "text": "Save record"}
    clear = {"type": "CLICK_TEXT", "text": "Clear all"}
    cases = [
        ("fill both and save", fill + [save], True),
        ("fill but never save", fill, False),
        ("save then undo it", fill + [save, clear], False),
        ("wrong value then save", [{"type": "FILL", "selector": "#name", "text": "beta"}, save], False),
        ("one field only then save", [{"type": "FILL", "selector": "#amount", "text": "4"}, save], False),
    ]

    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})
    disagreements = []
    for name, operations, is_really_successful in cases:
        verdict = BO.judge(browser, operations, "saved alpha = 4")
        says_done = verdict.get("verdict") == "EFFECT_CONFIRMED"
        if says_done != is_really_successful:
            disagreements.append((name, says_done, verdict))

    assert not disagreements, disagreements


def test_a_goal_that_states_nothing_to_look_for_is_refused(page_url: str) -> None:
    """The judge cannot invent its expectation; a goal that states none gets a refusal, not a guess."""
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})
    verdict = BO.judge(browser, [], "   ")
    assert verdict["judged"] is False
    assert verdict["why"] == "THE_GOAL_STATES_NOTHING_TO_LOOK_FOR", verdict


# ----------------------------------------------------------------------------------------------------
# A goal phrased like a person, against a page that never repeats it.
# ----------------------------------------------------------------------------------------------------

def test_a_goal_with_no_words_in_common_with_the_page_is_still_judged(page_url: str) -> None:
    """THE LIMIT §A104 NAMED AS UNSOLVED, solved by asking a different question.

    `save a record named "alpha" with amount "4"` shares NO verbatim substring with the page that fulfils
    it (`saved alpha = 4`). Judged by string containment the answer is a refusal, and a refusal on a page
    that did exactly what was asked is the mirror of the bug this module exists to prevent.

    What a person checks is not whether the page repeats their sentence -- it is whether THEIR VALUES
    landed. The values come from the goal's own quoted spans. Nothing is inferred and no synonym is needed:
    `save` never has to mean anything.
    """
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})

    goal = 'save a record named "alpha" with amount "4"'
    values = BO.stated_values(goal)
    assert values == ["alpha", "4"], values

    verdict = BO.judge(browser, [
        {"type": "FILL", "selector": "#name", "text": "alpha"},
        {"type": "FILL", "selector": "#amount", "text": "4"},
        {"type": "CLICK_TEXT", "text": "Save record"},
    ], "", values=values)

    assert verdict["judged"] is True, verdict
    assert verdict["verdict"] == "EFFECT_CONFIRMED", verdict
    assert verdict["looked_for"] == "alpha AND 4"
    assert verdict["missing_after"] == []


def test_a_field_word_is_never_taken_as_its_own_value() -> None:
    """THE FALSE CONFIRMATION I BUILT AND CAUGHT IN THE SAME MINUTE.

    The first version captured `amount` as the value in `with amount 4` -- because `amount` is where a value
    goes. A judge fed that would confirm any page containing the WORD "amount" while the amount itself was
    wrong, which is worse than refusing: it is a false confirmation wearing the costume of a real one.

    `set qty 8 for sku B2` then yielded `['sku', '8']` for the same reason. Field nouns are excluded now.

    THE HONEST LIMIT THIS TEST ALSO PINS: `sku B2` drops `B2`, so the check is weaker than the request. A
    judge that checks fewer values than the goal stated can confirm on less evidence than it claims. That is
    the safe direction of error -- under-extraction refuses, over-extraction falsely confirms -- but it is
    still an error and it is recorded here rather than left to be discovered as a false pass.
    """
    assert BO.stated_values('save a record named alpha with amount 4') == ["alpha", "4"]
    assert BO.stated_values('save a record named "alpha" with amount "4"') == ["alpha", "4"]
    assert BO.stated_values("set the owner to alice") == ["alice"]
    assert BO.stated_values("set qty 8 for sku B2") == ["8"]        # B2 is lost: the stated limitation
    assert "amount" not in BO.stated_values("with amount 4")
    assert "sku" not in BO.stated_values("for sku B2")


# ----------------------------------------------------------------------------------------------------
# Success as a RELATIONSHIP, not a value.
# ----------------------------------------------------------------------------------------------------

_BOARD = """<!doctype html><html><head><title>Board</title></head><body>
<div id="board">
  <div id="todo"><h2>Todo</h2><div class="card" id="card">fix login</div></div>
  <div id="done"><h2>Done</h2></div>
</div>
<script>
document.getElementById('card').onclick = () => {
  document.getElementById('done').appendChild(document.getElementById('card'));
};
</script></body></html>
"""


@pytest.fixture(scope="module")
def board_url():
    directory = tempfile.mkdtemp(prefix="board_")
    (pathlib.Path(directory) / "board.html").write_text(_BOARD)
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
        *args, directory=directory, **kwargs)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield "http://127.0.0.1:%d/board.html" % port
    finally:
        server.shutdown()
        shutil.rmtree(directory, ignore_errors=True)


def test_a_page_reports_where_its_words_are_not_only_what_they_are(board_url: str) -> None:
    """`elements` reports what can be pressed. A card and its column are neither, so without `regions` a
    board is invisible: measured, `elements: []` for a page holding a card and two columns."""
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": board_url})
    seen = BO.observe(browser)

    labels = [r.get("label") for r in seen["regions"]]
    assert "Todo" in labels and "Done" in labels, labels
    todo = next(r for r in seen["regions"] if r.get("label") == "Todo")
    assert "fix login" in todo["text"]


def test_a_goal_whose_success_is_containment_is_judged_from_structure(board_url: str) -> None:
    """THE CASE §A105 SAID WAS UNSOLVED, and it could not be solved with text.

    "move the task to Done" is a statement about CONTAINMENT. Every text judge in this module is blind to
    it: the words on the board do not change in any way that identifies which column holds the card. Read
    from regions, the answer is a fact -- Todo holds it before, Done holds it after.
    """
    browser = browser_v1.bind()
    verdict = BO.judge_placement(browser, [{"type": "CLICK_TEXT", "text": "fix login"}],
                                 "fix login", "Done")

    assert verdict["judged"] is True, verdict
    assert verdict["verdict"] == "PLACEMENT_CONFIRMED", verdict
    assert verdict["was_in"] == "Todo", verdict
    assert verdict["now_in"] == "Done", verdict
    assert verdict["ops_all_passed"] is True


def test_a_thing_cannot_be_its_own_container(board_url: str) -> None:
    """THE BUG THAT MADE A CORRECT MOVE REPORT AS UNCONFIRMED.

    The innermost region holding `fix login` is the CARD, whose label is empty -- so `was_in` and `now_in`
    were both `None` on a page where the move had plainly happened, and the verdict was
    `PLACEMENT_NOT_CONFIRMED`. A thing cannot be its own container; the container is the nearest ancestor a
    person could NAME.
    """
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": board_url})
    seen = BO.observe(browser)

    where = BO._smallest_region_holding(BO.regions_of(seen), "fix login")
    assert where is not None
    assert where.get("label") == "Todo", where          # named ancestor, not the unlabelled card
    assert where.get("text", "").strip() != "fix login"


def test_a_placement_already_true_is_not_evidence_and_a_missing_container_refuses(board_url: str) -> None:
    """The two refusals a placement judge needs, and both are the same principle as §A105's."""
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": board_url})
    browser.act({"type": "CLICK_TEXT", "text": "fix login"})

    repeated = BO.judge_placement(browser, [], "fix login", "Done")
    assert repeated["verdict"] == "THE_THING_WAS_ALREADY_THERE", repeated

    absent = BO.judge_placement(browser, [], "fix login", "Archive")
    assert absent["judged"] is False
    assert absent["why"] == "THE_CONTAINER_NAMED_IS_NOT_ON_THE_PAGE", absent
    assert "Done" in absent["labels"]
