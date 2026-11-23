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


def test_a_goal_that_states_nothing_to_look_for_is_refused(page_url: str) -> None:
    """The judge cannot invent its expectation; a goal that states none gets a refusal, not a guess."""
    browser = browser_v1.bind()
    browser.act({"type": "NAVIGATE", "url": page_url})
    verdict = BO.judge(browser, [], "   ")
    assert verdict["judged"] is False
    assert verdict["why"] == "THE_GOAL_STATES_NOTHING_TO_LOOK_FOR", verdict
