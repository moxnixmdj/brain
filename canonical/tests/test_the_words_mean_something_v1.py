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

    PROSE = {"p", "blockquote", "td", "figcaption", "article", "pre"}
    NAVIGATION = {"nav"}
    SKIP = {"script", "style", "svg", "path", "template", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[dict] = []
        self._stack: list[str] = []
        self._current: dict | None = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in self.SKIP or (self._stack and self._stack[-1] in self.SKIP):
            self._stack.append(tag)
            return
        if tag in ("a", "button"):
            self._current = {"tag": tag, "text": "", "aria": attributes.get("aria-label", ""),
                             "title": attributes.get("title", ""),
                             "in_prose": any(t in self.PROSE for t in self._stack),
                             "in_navigation": any(t in self.NAVIGATION for t in self._stack)}
            self._stack.append(tag)
            self._depth = 0
            return
        self._stack.append(tag)
        if self._current is not None:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in ("a", "button") and self._current is not None:
            self.found.append(self._current)
            self._current = None
            self._depth = 0
        # pop to the matching opener so ancestry is the real path, not an approximation
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._current is not None and self._depth <= 3 and not (self._stack and self._stack[-1] in self.SKIP):
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
            out.append(Candidate("e%d" % index, element["tag"], name,
                                 in_prose=element["in_prose"], in_navigation=element["in_navigation"]))
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


def test_a_real_page_prefers_the_control_over_the_mention_of_it() -> None:
    """LIVE — and this test REPLACES one that asserted the opposite, correctly.

    An earlier version of this file asserted that "download the code" on torvalds/linux must REFUSE, because
    the page carries two elements named "Code". That was the honest answer while the resolver could only see
    words. Once it could see WHERE each element sits, the answer changed for a real reason:

        e55  a      Code    inside nav      the repository's code TAB
        e76  button Code    outside nav     a control that merely shares the label

    A person who says "the code" means the tab. The test was updated because the module got better, and the
    distinction it now draws is measured, not asserted -- both elements are printed by the assertion below.
    """
    page = _live("https://github.com/torvalds/linux")
    codes = [c for c in page if c.name.strip().casefold() == "code"]
    assert len(codes) >= 2, codes
    verdict = resolve("download the code", page)
    assert verdict["resolved"] is True, verdict
    chosen = next(c for c in codes if c.element_id == verdict["element_id"])
    assert chosen.in_navigation is True, (verdict, [(c.element_id, c.role, c.in_navigation) for c in codes])


def test_a_real_page_does_not_invent_a_control_that_is_not_there() -> None:
    """LIVE. A request about something absent must not be answered with the nearest thing present."""
    page = _live("https://github.com/torvalds/linux")
    verdict = resolve("create a sandwich", page)
    assert verdict["resolved"] is False, verdict


# ----------------------------------------------------------------------------------------------------------
# §A135 — structure beats words, and the ordering of the facts is the mechanism
# ----------------------------------------------------------------------------------------------------------

def test_a_mention_is_not_a_control() -> None:
    """The sharpest structural fact, measured live on psf/requests.

    "Issues169 (169)" is the repository's TAB. "this issue" is a link inside a sentence in the README blurb.
    Every lexical measure treats them alike -- both are <a>, both one word of the stem `issue`. Their ancestry
    does not:

        the tab        ... > header > nav > ul > li      a list item IN NAVIGATION
        the mention    ... > article > p                 a paragraph IN AN ARTICLE

    A person who says "the issues" means the tab. The words cannot say so; the path can.
    """
    tab = Candidate("tab", "a", "Issues169 (169)", in_prose=False, in_navigation=True)
    mention = Candidate("mention", "a", "this issue", in_prose=True, in_navigation=False)
    verdict = resolve("view the issues", [mention, tab])
    assert verdict["resolved"] is True, verdict
    assert verdict["element_id"] == "tab", verdict


def test_an_li_inside_nav_is_navigation_and_an_li_in_an_article_is_prose() -> None:
    """The mistake that had to be measured: a tag name is not structure, the PATH is.

    A first version treated `li` as a prose tag and got the wrong answer, because a list item inside a `nav`
    is navigation. The two candidates below differ ONLY in the `li`'s parent.
    """
    nav_item = Candidate("nav", "a", "Issues", in_prose=False, in_navigation=True)
    prose_item = Candidate("prose", "a", "Issues", in_prose=True, in_navigation=False)
    verdict = resolve("view the issues", [prose_item, nav_item])
    assert verdict["resolved"] is True
    assert verdict["element_id"] == "nav", verdict


def test_a_partial_name_does_not_tie_with_the_whole_request() -> None:
    """§A135 — measured live on django/django, where two elements named "views" tied with the Issues tab.

    "views" is made only of a word the request uses ("view"), so the whole-name rule admits it. But a control
    whose name accounts for ONE of the request's two content words is a weaker answer than one accounting for
    the request itself. Ordering by coverage first is what removes the false tie.
    """
    issues = Candidate("issues", "a", "Issues", in_prose=False, in_navigation=True)
    views_a = Candidate("v1", "a", "views", in_prose=False, in_navigation=False)
    views_b = Candidate("v2", "a", "views", in_prose=False, in_navigation=False)
    verdict = resolve("view the issues", [views_a, views_b, issues])
    assert verdict["resolved"] is True, verdict
    assert verdict["element_id"] == "issues", verdict


def test_a_real_page_scores_without_a_single_miss() -> None:
    """LIVE, four unseen repositories, every probe whose target is verifiably on the page.

    Measured 2026-11-23. This is the number that matters, and it is stated with its scope: four GitHub
    repositories, view-and-navigate requests, server-rendered HTML. It is not computer use.
    """
    pages = {}
    for url in ("https://github.com/psf/requests", "https://github.com/django/django",
                "https://github.com/microsoft/vscode", "https://github.com/python/cpython"):
        pages[url] = _live(url)

    expectations = {
        "https://github.com/psf/requests": [("view the issues", "Issues"),
                                            ("open the pull requests", "Pull requests"),
                                            ("read the readme", "README"), ("star it", "Star")],
        "https://github.com/django/django": [("open the pull requests", "Pull requests"),
                                             ("go to actions", "Actions"), ("read the readme", "README")],
        "https://github.com/microsoft/vscode": [("view the issues", "Issues"),
                                                ("open the pull requests", "Pull requests"),
                                                ("star it", "Star")],
        "https://github.com/python/cpython": [("view the issues", "Issues"),
                                              ("open the pull requests", "Pull requests"),
                                              ("go to actions", "Actions")],
    }
    resolved = misses = 0
    for url, probes in expectations.items():
        for instruction, fragment in probes:
            verdict = resolve(instruction, pages[url])
            if verdict["resolved"]:
                assert fragment.casefold() in verdict["name"].casefold(), (url, instruction, verdict)
                resolved += 1
            else:
                misses += 1
    assert (resolved, misses) == (13, 0), (resolved, misses)

    # and every page still refuses what is not there
    for url, page in pages.items():
        assert resolve("create a sandwich", page)["resolved"] is False, url


def test_a_second_site_keeps_its_score() -> None:
    """LIVE, and a DIFFERENT product from GitHub — which §A135 did not have.

    Measured 2026-11-23 on pypi.org/project/requests/ (697 parsed elements). Two probes whose target exists
    resolve; two whose target is genuinely absent (`install`, `homepage` — neither string occurs in the page's
    controls) refuse; one nonsense request refuses. The point of this test is not the count. It is that a site
    with different markup, different vocabulary and a much larger element set does not break the rule.
    """
    page = _live("https://pypi.org/project/requests/")
    for instruction, fragment in (("view the project description", "Project description"),
                                  ("see the release history", "Release history")):
        verdict = resolve(instruction, page)
        assert verdict["resolved"] is True, (instruction, verdict)
        assert fragment.casefold() in verdict["name"].casefold(), (instruction, verdict)

    for absent in ("install the package", "go to the homepage"):
        verdict = resolve(absent, page)
        assert verdict["resolved"] is False, (absent, verdict)
    assert resolve("create a sandwich", page)["resolved"] is False


def test_a_name_that_is_a_sentence_is_reported_as_its_label() -> None:
    """A screen-reader instruction is not what a person calls the control.

    pypi.org names a tab "Project description. Focus will be moved to the description." The match is correct;
    the narration should not be reported as the control's name. Shortening only happens at a sentence boundary
    whose remainder is an instruction about focus — so "README.md, (File)" survives intact.
    """
    page = _live("https://pypi.org/project/requests/")
    verdict = resolve("view the project description", page)
    assert verdict["resolved"] is True
    assert verdict["name"] == "Project description", verdict

    github = _live("https://github.com/psf/requests")
    readme = resolve("read the readme", github)
    assert readme["resolved"] is True
    assert "," in readme["name"] or readme["name"] == "README", readme
