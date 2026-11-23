"""The observer's two honesty rules, tested with NO BROWSER AT ALL.

Why this file exists apart from `test_browser_observer_v1.py`. That file marks its whole module
skipif-no-Chromium, which is right for the tests that drive a live page -- and wrong for these two, which
build a fake snapshot and need no browser. Placed there they were silently skipped on any machine without
Chromium (measured 2026-11-23: 14 skipped, 0 run), so the fixes they pin were never actually executed.

The defect they guard is the one that survives a fix: §A125 made the observer ADMIT a partial read; §A126 made
the judge HONOUR the admission. Recording a limit is not honouring it, and a test that never runs is not a test.
"""
from __future__ import annotations

import pytest

from canonical.runtime import browser_observer_v1 as BO

def test_a_truncated_read_is_reported_as_partial_and_never_as_the_whole_page() -> None:
    """§A125: THE BROWSER HAD THE SAME DEFECT §A119 FOUND IN THE CODE WALKER, and this is the transfer.

    `observe()` cut `text` at `max_text` and returned `ok: True` with no record of the cut. On a page of 12,000
    characters the caller received 8,000 and could not tell whether it had seen the page or only part of it — so a
    searcher could report "not on the page" about text it had never looked at. That is the dishonest verdict, in
    the one organ that reads the most.

    The fix is the same as §A119's: record the refusal. `text_truncated`, `text_total`, `text_not_seen` and `eye`
    travel with the observation, so a caller that ignores them ignores a stated fact rather than a hidden one.
    """

    class _Page:
        def __init__(self, text: str) -> None:
            self.text = text

        def snapshot(self) -> dict:
            return {"pages": [{"url": "u", "title": "t", "text": self.text,
                               "elements": [], "regions": []}], "page_count": 1}

    long_page = BO.observe(_Page("A" * 12000), max_text=8000)
    assert long_page["ok"] is True
    assert len(long_page["text"]) == 8000
    assert long_page["text_truncated"] is True
    assert long_page["text_total"] == 12000
    assert long_page["text_not_seen"] == 4000
    assert long_page["eye"] == "PARTIAL_READ"

    short_page = BO.observe(_Page("short"), max_text=8000)
    assert short_page["text_truncated"] is False
    assert short_page["text_not_seen"] == 0
    assert short_page["eye"] == "WHOLE_READ"
    assert short_page["text"] == "short"


def test_a_negative_finding_from_a_partial_read_is_re_read_before_it_is_believed() -> None:
    """§A126: THE MIRROR OF §A119 — a false FAILURE, not a false clean.

    §A125 made `observe()` admit that its read was partial. Recording the limit was not enough: `judge()` ran
    `value in after_text` over the truncated string, so evidence past the cutoff read as ABSENT. Measured: a
    value at char 9000 of a 12,000-char page made a completed save report as a failure -- and a system that
    believes that will redo work it has already done, forever.

    A negative finding from a partial read is not a finding. When the evidence is not found and the read was
    partial, `judge()` asks again with no limit. And because a verdict rescued by a second look is weaker than
    one proved by the first, `evidence_rests_on` says which it was.
    """

    long_page = "A" * 9000 + "saved 42"

    class _Page:
        def __init__(self, text: str) -> None:
            self.text = text

        def snapshot(self) -> dict:
            return {"pages": [{"url": "u", "title": "t", "text": self.text,
                               "elements": [], "regions": []}], "page_count": 1}

        def act(self, operation: dict) -> dict:
            return {"status": "ok"}

    # evidence past the cutoff: a false failure without the re-read
    rescued = BO.judge(_Page(long_page), [{"type": "click"}], "", values=["saved 42"])
    assert rescued["judged"] is True
    assert rescued["verdict"] == "EFFECT_CONFIRMED", rescued
    assert rescued["evidence_rests_on"] == "REREAD_OF_WHOLE_PAGE"

    # the first read already answered: no re-read, and the verdict says so
    first = BO.judge(_Page("x saved 42"), [{"type": "click"}], "", values=["saved 42"])
    assert first["judged"] is True
    assert first["evidence_rests_on"] == "FIRST_READ"

    # truly absent: the negative now rests on the WHOLE page, not on a partial one
    absent = BO.judge(_Page(long_page), [{"type": "click"}], "", values=["never appears"])
    assert absent["verdict"] == "EFFECT_ABSENT"
    assert absent["evidence_rests_on"] == "REREAD_OF_WHOLE_PAGE", "absence must be proved on the whole page"

    # and the no-limit read itself is honest about being whole
    whole = BO.observe(_Page(long_page), max_text=None)
    assert whole["text_truncated"] is False and whole["eye"] == "WHOLE_READ"
    assert "saved 42" in whole["text"]
