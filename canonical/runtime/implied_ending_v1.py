#!/usr/bin/env python3
"""A SENTENCE DOES NOT NEED TO SAY "SUBMIT" FOR THE PAGE TO GRADED IT ON SUBMIT.

The defect, measured not guessed
--------------------------------
On 2026-11-16 the instruction arm was measured on 130 real MiniWoB++ pages in a real chromium
substrate: **52 solved, and 78 not**. Then the *reason each episode stopped* was recorded, which
the refusal census had never done:

    THE_ARM_HAD_NOTHING_LEFT_TO_SAY   59
    THE_PAGE_FAILED_IT                19
    BUDGET                             0
    SUCCEEDED                         52

No page ever ran out of actions. The arm stopped because it had said everything it could say. That
is a different failure from "the page failed it", and it is a different failure from "a word is
missing", and it was invisible in every previous census.

Of the 19 the page failed, five are the drag family. Reading the pages' OWN success checks:

    drag-box.html:   $('#subbtn').on('click', ... core.endEpisode(smallBoxContained() ? 1 : -1))
    drag-cube.html:  the same shape

The page grades on a press of `#subbtn`, whose visible word is **Submit**. The instruction is
"Drag the smaller box so that it is completely inside the larger box." -- it never says Submit.
The arm dragged the box correctly (measured: the small box moves to [94,86,28,28], inside the
larger [73,75,58,58]) and then stopped one unstated press short. Submitting with nothing done
scores -1 on all five; submitting with `drag-cube` untouched scores **+1**, because that page
starts in a winning layout.

So the missing word is not "drag". It is **"the page has a way of saying it is finished, and the
sentence does not have to name it"**.

What this module is, and what it refuses to be
----------------------------------------------
An **implied ending**: when the page carries exactly one control whose own name means "deliver
this", and the instruction's own acts have all been carried out, the ending is implied.

It refuses in the cases that matter:

  * the control's name must be an ending word, from a closed list -- not "the last button";
  * it must be UNIQUE on the page. Two buttons called Submit is that page's job to disambiguate,
    not ours to guess;
  * it is never emitted before the instruction's own acts. Pressing Submit on an empty form is
    exactly the trace a wrong answer makes, and the policy already refuses to act on half a
    contract for the same reason;
  * if the sentence explicitly says NOT to submit, no ending is implied.

Authority NONE. No reward is read, no model is used, nothing is remembered between pages. The
ending is derived from the instruction and the observation on every look.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_IMPLIED_ENDING_V1"

#: Words a page uses to name the act of delivering what was asked for. Closed on purpose: an
#: open list would make "the control with any sensible name" a rule, which is a guess.
ENDING_WORDS = ("submit", "done", "finish", "finished", "confirm", "ok", "apply", "send", "save",
                "check", "verify", "continue", "next")

#: A sentence that says NOT to end. If a page offers Submit and the words say "do not submit",
#: implying the ending would be obeying the page and disobeying the instruction.
_REFUSES_AN_ENDING = re.compile(
    r"\b(?:do not|don't|without|never)\s+(?:press|click|hit|submit)", re.IGNORECASE)

IMPLIED = "IMPLIED__THE_PAGE_HAS_ONE_WAY_TO_SAY_THIS_IS_FINISHED"
ABSENT = "ABSENT__THE_PAGE_OFFERS_NO_WAY_TO_SAY_THIS_IS_FINISHED"
AMBIGUOUS = "AMBIGUOUS__THE_PAGE_OFFERS_MORE_THAN_ONE_WAY"
FORBIDDEN = "FORBIDDEN__THE_INSTRUCTION_SAYS_NOT_TO_FINISH"


@dataclass(frozen=True)
class Ending:
    outcome: str
    index: int | None = None
    word: str = ""
    candidates: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "outcome": self.outcome, "index": self.index,
                "word": self.word, "candidates": list(self.candidates)}


def _own_words(element: Mapping[str, Any]) -> str:
    """What the element says about itself. Never its subtree: `full_text` is how an ancestor
    'shows' everything (measured 2026-11-16, on identity)."""
    parts = [str(element.get("text") or ""), str(element.get("value") or "")]
    parts += [str(element.get(key) or "") for key in ("aria-label", "title", "alt")]
    return " ".join(parts).strip().lower()


def find_ending(instruction: str, observation: Mapping[str, Any], *,
                only: Sequence[int] | None = None) -> Ending:
    """The one control that ends this task, or a named reason there is none.

    `only` restricts the search to a set of indices -- the caller uses it to ask the question
    "was this element the page's ending?" without re-deciding it.
    """
    if _REFUSES_AN_ENDING.search(instruction or ""):
        return Ending(FORBIDDEN)

    elements = list(observation.get("elements") or [])
    pool: Iterable[Mapping[str, Any]] = elements
    if only is not None:
        wanted = {int(i) for i in only}
        pool = [e for e in elements if int(e.get("index", -1)) in wanted]

    hits = []
    for element in pool:
        if not element.get("can_click"):
            continue
        said = _own_words(element)
        if not said:
            continue
        words = set(re.findall(r"[a-z]+", said))
        # the element's OWN word must be an ending word -- not merely contain one
        matched = [w for w in ENDING_WORDS if w in words]
        if matched:
            hits.append((int(element["index"]), matched[0]))

    if not hits:
        return Ending(ABSENT)
    if len(hits) > 1:
        return Ending(AMBIGUOUS, candidates=tuple(sorted(i for i, _ in hits)))
    index, word = hits[0]
    return Ending(IMPLIED, index=index, word=word, candidates=(index,))


def might_need_an_ending(instruction: str, observation: Mapping[str, Any]) -> bool:
    """Whether this episode could end on a press the sentence never names.

    The cheap half of the question, used to decide whether to ask the expensive half. A sentence
    that already asks for a press at the end does not need an implied ending, because it has an
    explicit one.
    """
    low = (instruction or "").lower()
    if re.search(r"\b(submit|press|click|hit|confirm|finish|done)\b", low):
        return False
    return find_ending(instruction, observation).outcome == IMPLIED
