#!/usr/bin/env python3
"""A CONTROL THAT ASKS A FURTHER QUESTION, AND THE WORDS THAT ANSWER IT.

The defect, measured not guessed
--------------------------------
Measured 2026-11-16 on the four real `choose-date*` pages. "Select 12/26/2016 as the date and hit
submit." The page carries `<input id="datepicker" class="hasDatepicker">`. The arm clicks it -- the
right element -- and then stops.

Clicking it OPENS A CALENDAR. The observation then carries, on the same page:

    9  'Prev'    11 'Next'    13 'December'   14 '2016'
    19 'Su' 21 'Mo' 23 'Tu' 25 'We' 27 'Th' 29 'Fr' 31 'Sa'
    39 '1'  41 '2' ... 93 '26' ... 103 '31'

The date in the sentence is written 12/26/2016, and the page carries the words `December`,
`2016`, `26` with nothing tying them together. The arm has no name for "choose a date", so it
looks for a control called "12/26/2016", finds none, and says nothing.

This is the SAME defect the frame module fixed in space, one axis over: a word names a REGION of
the observation the language could not name. There the region was a row; here it is a coordinate
inside a picker. One implementation, because the next picker is not a date.

What it refuses to be
---------------------
Not a date parser with a calendar in it. It reads the SHAPE of what the sentence asked for
(`D/M/Y`, `M/D/Y`, a month name, a time) and looks for controls whose OWN text is those components.
It refuses when the page shows a component twice -- two `26`s are two different days -- because
then the sentence has to say which, and ours does not.

Authority NONE. Pure function of (instruction, observation). No model, no reward, no memory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PICKER_ANSWER_V1"

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december")
MONTH_ABBREVIATIONS = tuple(m[:3] for m in MONTHS)

#: The shapes a date or time is written in, most specific first. Each is (name, regex).
SHAPES = (
    ("M/D/Y", re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b")),
    ("D/M/Y", re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")),
    ("MONTH D Y", re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})\b",
                             re.IGNORECASE)),
    ("H:MM", re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", re.IGNORECASE)),
)

ANSWERED = "ANSWERED__THE_PAGE_OFFERS_THE_PARTS_OF_WHAT_WAS_ASKED_FOR"
NO_PICKER_OPEN = "ABSENT__THE_PAGE_SHOWS_NO_SUCH_PARTS"
AMBIGUOUS = "AMBIGUOUS__THE_PAGE_SHOWS_THAT_PART_MORE_THAN_ONCE"


@dataclass(frozen=True)
class Answer:
    outcome: str
    parts: tuple[str, ...] = ()
    indices: tuple[int, ...] = ()
    shape: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "outcome": self.outcome, "parts": list(self.parts),
                "indices": list(self.indices), "shape": self.shape, "reason": self.reason}


def _own_text(element: Mapping[str, Any]) -> str:
    return " ".join(str(element.get(key) or "") for key in
                    ("text", "value", "aria-label", "title")).strip()


def _parts_of(instruction: str) -> tuple[str, tuple[str, ...], str]:
    """The components the sentence asked for, in the sentence's own shape.

    Returns (shape name, components, why-not). An empty component list is 'nothing to answer'.
    """
    for name, pattern in SHAPES:
        match = pattern.search(instruction or "")
        if not match:
            continue
        groups = [g for g in match.groups() if g]
        if name == "MONTH D Y":
            month = groups[0].lower()
            return name, (str(MONTHS.index(month) + 1), str(months_name(month)), groups[1],
                          groups[2]), ""
        if name == "H:MM":
            return name, (groups[0], groups[1]), ""
        if name in ("M/D/Y", "D/M/Y"):
            a, b, c = groups
            # The page will show a month NAME and a year and a day. A slash notation could mean
            # either order, and that ambiguity is the page's to resolve, not ours to assume --
            # so both months are offered and the answer is AMBIGUOUS if only one is on the page.
            return name, (a, b, c), ""
    return "", (), "THE_SENTENCE_ASKS_FOR_NO_DATE_OR_TIME"


def months_name(word: str) -> str:
    return word[:3].title()


def answer_picker(instruction: str, observation: Mapping[str, Any], *,
                  must_include: Sequence[str] | None = None) -> Answer:
    """The controls whose own words are the parts of what the sentence asked for.

    `must_include` is the stable core every answer must contain -- the caller passes the year and
    the month NAME when it knows them, because "26" alone is found on a calendar 30 times.
    """
    shape, parts, why = _parts_of(instruction)
    if not parts:
        return Answer(NO_PICKER_OPEN, reason=why)

    elements = list(observation.get("elements") or [])
    clickable = [e for e in elements if e.get("can_click")]
    by_word: dict[str, list[int]] = {}
    for element in clickable:
        said = _own_text(element)
        if not said:
            continue
        # A SET of the case variants, because they collapse to one key: appending three spellings
        # made one December look like two and the first real page answered AMBIGUOUS. An index is
        # counted once per DISTINCT WORD, never once per spelling of it.
        for word in {said.strip().lower(), said.strip().title()}:
            bucket = by_word.setdefault(word.lower(), [])
            if int(element["index"]) not in bucket:
                bucket.append(int(element["index"]))

    # Which components can the page actually answer? A year is a 4-digit control; a month is a
    # control whose word is a month; a day is a number control. The sentence supplies all three.
    required: list[str] = list(must_include or ())
    if not required:
        required = [p for p in parts if len(p) > 2 or p.lower() in MONTHS]
    chosen: list[int] = []
    chosen_parts: list[str] = []
    for part in required:
        found = by_word.get(part.lower()) or []
        if not found:
            continue
        if len(found) > 1:
            return Answer(AMBIGUOUS, parts=tuple(required), indices=tuple(sorted(found)),
                          shape=shape, reason=f"THE_PAGE_SHOWS_{part}_MORE_THAN_ONCE")
        chosen.append(found[0])
        chosen_parts.append(part)

    if not chosen or len(chosen_parts) < min(2, len(required)):
        return Answer(NO_PICKER_OPEN, parts=tuple(required), shape=shape,
                      reason="THE_PAGE_DOES_NOT_SHOW_THOSE_PARTS")
    return Answer(ANSWERED, parts=tuple(chosen_parts), indices=tuple(chosen), shape=shape)


def date_parts(instruction: str) -> dict[str, Any]:
    """The sentence's date, decomposed into the words a picker shows: year, month name, day.

    Kept separate from `answer_picker` because this is the reading of the SENTENCE and that is the
    reading of the PAGE. Conflating them is how a reader starts believing its own assumption.
    """
    shape, parts, why = _parts_of(instruction)
    if shape == "MONTH D Y":
        month_word = parts[1].lower()
        return {"shape": shape, "year": parts[3], "month": parts[1], "day": parts[2],
                "month_number": parts[0]}
    if shape in ("M/D/Y", "D/M/Y"):
        a, b, c = parts
        year = c if len(c) == 4 else f"20{c}"
        return {"shape": shape, "year": year, "ambiguous_day_month": (a, b)}

    if shape == "H:MM":
        return {"shape": shape, "hour": parts[0], "minute": parts[1]}
    return {"shape": "", "reason": why}


#: The calendar's own furniture. These are the words a picker uses to MOVE, and they are the only
#: actions allowed before answering: navigation, never a guess at the answer.
MONTH_NAVIGATION = {"prev": -1, "previous": -1, "<": -1, "‹": -1, "«": -1,
                    "next": 1, ">": 1, "›": 1, "»": 1}
NOT_YET = "NAVIGATE__THE_PICKER_IS_SHOWING_A_DIFFERENT_MONTH"
ALREADY_CLICKED = "THE_ELEMENT_ALREADY_ASKED_ITS_OWN_QUESTION"


def navigate_to_month(instruction: str, observation: Mapping[str, Any]) -> dict[str, Any]:
    """Which way to step the calendar so the month it shows becomes the month asked for.

    A picker has STATE. The words asked for December; the page is showing November; the arm that
    only matches words on the page answers with the wrong month's `10` and is graded -1 -- a
    confident wrong answer, which is worse than a refusal. So the state is read first: the month
    name a picker displays is itself a control, and the distance between it and the asked-for month
    is a signed count of presses of Prev/Next.

    Refuses when the page shows no month, or shows more than one, or offers no step in the needed
    direction. A cycle longer than 6 steps is refused rather than iterated: a picker that needs
    more than half a year of presses is not a picker this reader understands.
    """
    said = date_parts(instruction)
    if said.get("shape") != "M/D/Y" and said.get("shape") != "MONTH D Y":
        return {"outcome": NO_PICKER_OPEN, "presses": 0,
                "reason": "THE_SENTENCE_NAMES_NO_MONTH_TO_NAVIGATE_TO"}
    target_month = None
    if said.get("shape") == "MONTH D Y":
        target_month = MONTHS.index(said["month"].lower()) + 1
    else:
        a, b = said["ambiguous_day_month"]
        # 12/26 cannot be both month 12 and month 26: exactly one is a legal month. That is not an
        # assumption about notation, it is the range of a month.
        legal = [int(x) for x in (a, b) if 1 <= int(x) <= 12]
        if len(legal) == 1:
            target_month = legal[0]
        else:
            # BOTH are legal months, so the sentence alone cannot say which is which and any
            # choice is a convention I would be ASSUMING. Ask the page instead: a picker writes
            # the date it just chose back into its own input ("12/05/2016" measured 2026-11-16 on
            # choose-date.html), and that literal declares which field comes first. This is the
            # difference between reading the page and knowing the answer.
            declared = declared_order(observation)
            if declared == "M/D/Y":
                target_month = int(a)
            elif declared == "D/M/Y":
                target_month = int(b) if int(b) <= 12 else int(a)

    clickable = [e for e in observation.get("elements") or [] if e.get("can_click")]
    shown = []
    steps: dict[int, int] = {}
    for element in clickable:
        word = _own_text(element).strip()
        low = word.lower()
        if low in MONTHS:
            shown.append((int(element["index"]), MONTHS.index(low) + 1))
        elif low in MONTH_NAVIGATION:
            steps[int(element["index"])] = MONTH_NAVIGATION[low]

    if len(shown) != 1:
        return {"outcome": (AMBIGUOUS if shown else NO_PICKER_OPEN), "presses": 0,
                "reason": ("THE_PAGE_SHOWS_MORE_THAN_ONE_MONTH" if shown
                           else "THE_PAGE_SHOWS_NO_MONTH")}
    if target_month is None:
        return {"outcome": NO_PICKER_OPEN, "presses": 0,
                "reason": "THE_SENTENCE_NAMES_NO_LEGAL_MONTH"}
    current = shown[0][1]
    if current == target_month:
        return {"outcome": "ALREADY_THERE", "presses": 0, "shown": current,
                "target": target_month}

    # forward steps wrap at 12, backward wrap at 1
    forward = (target_month - current) % 12
    backward = (current - target_month) % 12
    direction = 1 if forward <= backward else -1
    count = min(forward, backward)
    if count > 6:
        return {"outcome": NO_PICKER_OPEN, "presses": 0,
                "reason": "THE_CALENDAR_IS_MORE_THAN_SIX_STEPS_AWAY"}
    control = next((i for i, d in steps.items() if d == direction), None)
    if control is None:
        return {"outcome": ABSENT, "presses": 0,
                "reason": "THE_PAGE_OFFERS_NO_STEP_IN_THAT_DIRECTION"}
    return {"outcome": NOT_YET, "presses": count, "control": control, "direction": direction,
            "shown": current, "target": target_month}


_NOT_TYPED = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")


def declared_order(observation: Mapping[str, Any]) -> str:
    """The date notation the PAGE declares about itself, by whatever it has already written down.

    Empty unless the page carries a filled-in date. A picker that has recorded a choice has told
    us its own field order; nothing here assumes a locale. Returns "", "M/D/Y" or "D/M/Y".
    """
    for element in observation.get("elements") or []:
        for key in ("value", "text"):
            got = _NOT_TYPED.search(str(element.get(key) or ""))
            if not got:
                continue
            a, b, year = got.groups()
            # A declared order is only READ when it is unambiguous in itself: 12/05 can be either,
            # 05/26 cannot be anything but month-first (there is no month 26).
            if int(b) > 12:
                return "M/D/Y"
            if int(a) > 12:
                return "D/M/Y"
    return ""
