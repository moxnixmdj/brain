"""§A134 — from what a person said to which element they meant, with no model, measured on real pages.

WHY THIS IS THE ORGAN THAT MATTERED. Measured 2026-11-23, before this module existed:

    ground_consensus_action(action="click", role="button", name="Compose")   -> SELECT          (works)
    ground_consensus_action(action="click", role="button", name="write a new email")
                                                                            -> ESCALATE
                                                                               NO_CONSENSUS_MATCH

`consensus_dom_grounding` says of itself, correctly, that it "does not infer a target from a goal". It answers
*is this target unambiguous* and never *which element did they mean*. Every computer-use number in this
repository is unmeasured because nothing answered the second question — and nothing could be, because there was
no path from instructions to elements at all.

THE TESTS BELOW ARE IN TWO KINDS, AND THE SPLIT IS THE POINT:

    OFFLINE     a page written here, so the assertions are exact and re-runnable with no network
    LIVE        two real GitHub pages fetched at test time, which the module was NOT written against

The live tests are marked `live` and are skipped when the network is unavailable. They are the honest measure;
the offline ones only prove the mechanism is not broken.
"""
from __future__ import annotations

import html.parser
import urllib.request

import pytest

from canonical.runtime.what_the_words_mean_v1 import Candidate, resolve, stem, words

MAIL = [
    Candidate("e1", "button", "Compose"),
    Candidate("e3", "link", "Inbox"),
    Candidate("e4", "link", "Drafts"),
    Candidate("e5", "button", "Send"),
    Candidate("e6", "textbox", "Subject"),
    Candidate("e7", "button", "Archive"),
    Candidate("e9", "link", "Settings"),
]


# ----------------------------------------------------------------------------------------------------------
# the mechanism
# ----------------------------------------------------------------------------------------------------------

def test_a_word_the_page_uses_is_found_without_any_knowledge() -> None:
    """`check my inbox` -> the Inbox. Both say "inbox"; no synonym, no knowledge, no model."""
    for instruction, expected in (("check my inbox", "e3"), ("look at the drafts", "e4"),
                                  ("compose a message", "e1"), ("archive the conversation", "e7"),
                                  ("send this", "e5")):
        verdict = resolve(instruction, MAIL)
        assert verdict["resolved"] is True, (instruction, verdict)
        assert verdict["element_id"] == expected, (instruction, verdict)


def test_nothing_on_the_page_is_a_refusal_not_a_guess() -> None:
    """A request about something the page does not have must not become the nearest control."""
    for instruction in ("delete everything", "make me a sandwich", "print the invoice"):
        verdict = resolve(instruction, MAIL)
        assert verdict["resolved"] is False, (instruction, verdict)
        assert verdict["why"] in {"NO_ELEMENT_IS_NAMED_BY_A_WORD_OF_THE_REQUEST",
                                  "ONLY_FURNITURE_WORDS"}, (instruction, verdict)


def test_two_equally_named_elements_are_a_refusal() -> None:
    """§A74: when the evidence does not choose, return nothing. A coin flip is not an answer."""
    page = [Candidate("a", "link", "Code"), Candidate("b", "button", "Code")]
    verdict = resolve("download the code", page)
    assert verdict["resolved"] is False
    assert verdict["why"] == "THE_PAGE_DOES_NOT_CHOOSE"
    assert set(verdict["tied"]) == {"a", "b"}


def test_a_means_relation_is_used_only_when_it_has_a_source() -> None:
    """`write a new email` shares no word with `Compose`. That gap is closed by a written relation, or not at all."""
    gap = resolve("write a new email", MAIL)
    assert gap["resolved"] is False, gap

    # unattributed synonyms are guesses wearing a citation, so a relation without a source is not used
    unattributed = resolve("write a new email", MAIL, relations={"write a new email": "Compose"})
    assert unattributed["resolved"] is False, unattributed

    attributed = resolve("write a new email", MAIL, relations={"write a new email": "Compose"},
                         source="the mail provider's own help page")
    assert attributed["resolved"] is True
    assert attributed["element_id"] == "e1"
    assert attributed["source"] == "the mail provider's own help page"


def test_a_counter_glued_to_a_label_is_not_part_of_its_name() -> None:
    """Measured on a live page: GitHub renders the issues tab as "Issues5k+ (5k+)". Before the fix that made
    the word people say unrecognisable, and a word plainly on the page failed to match."""
    assert words("Issues5k+ (5k+)") == ["issues"]
    assert words("Pull requests2.4k (2.4k)") == ["pull", "requests"]
    assert words("36.6k forks") == ["forks"]
    assert stem("composing") == stem("compose")


# ----------------------------------------------------------------------------------------------------------
# live pages the module was not written against
# ----------------------------------------------------------------------------------------------------------

class _Elements(html.parser.HTMLParser):
    """Just enough parsing to get named controls off a real page. No browser, no JavaScript."""

    def __init__(self) -> None:
        super().__init__()
        self.found: list[dict] = []
        self._current: dict | None = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in ("a", "button"):
            self._current = {"tag": tag, "text": "", "aria": attributes.get("aria-label", ""),
                             "title": attributes.get("title", "")}
            self._depth = 0
        elif self._current is not None:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in ("a", "button") and self._current is not None:
            self.found.append(self._current)
            self._current = None
            self._depth = 0
        elif self._current is not None and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if self._current is not None and self._depth <= 2:
            self._current["text"] += data


def _page(url: str) -> list[Candidate]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    document = urllib.request.urlopen(request, timeout=30).read().decode("utf-8", "replace")
    parser = _Elements()
    parser.feed(document)
    out: list[Candidate] = []
    for index, element in enumerate(parser.found):
        name = (element["aria"] or element["title"] or " ".join(element["text"].split())).strip()[:60]
        if name:
            out.append(Candidate("e%d" % index, element["tag"], name))
    return out


def _live(url: str) -> list[Candidate]:
    try:
        page = _page(url)
    except Exception as error:  # noqa: BLE001 - any network failure means "not measurable", not "failed"
        pytest.skip("network unavailable: %s" % error)
    if not page:
        pytest.skip("no named elements parsed from %s" % url)
    return page


def test_a_real_page_says_the_words_plainly_on_it() -> None:
    """LIVE. The words a person uses for a tab are the words the tab is labelled with.

    Scored on https://github.com/python/cpython, which was NOT the page the module was developed against.
    """
    page = _live("https://github.com/python/cpython")
    for instruction, expected_fragment in (("view the issues", "Issues"),
                                           ("open the pull requests", "Pull requests"),
                                           ("go to actions", "Actions")):
        verdict = resolve(instruction, page)
        assert verdict["resolved"] is True, (instruction, verdict)
        assert expected_fragment.casefold() in verdict["name"].casefold(), (instruction, verdict)


def test_a_real_page_refuses_what_it_cannot_choose() -> None:
    """LIVE. Two elements both literally named "Code" are two different controls; the words do not pick one.

    This is the fail-closed rule holding on a real page rather than in a fixture: the refusal is correct even
    though a person with eyes would know which one they meant. Honest refusal over a confident coin flip.
    """
    page = _live("https://github.com/torvalds/linux")
    codes = [c for c in page if c.name.strip().casefold() == "code"]
    assert len(codes) >= 2, codes
    verdict = resolve("download the code", page)
    assert verdict["resolved"] is False
    assert verdict["why"] in {"THE_PAGE_DOES_NOT_CHOOSE", "NO_ELEMENT_IS_NAMED_BY_A_WORD_OF_THE_REQUEST"}


def test_a_real_page_does_not_invent_a_control_that_is_not_there() -> None:
    """LIVE. A request about something absent must not be answered with the nearest thing present."""
    page = _live("https://github.com/torvalds/linux")
    verdict = resolve("create a sandwich", page)
    assert verdict["resolved"] is False, verdict
