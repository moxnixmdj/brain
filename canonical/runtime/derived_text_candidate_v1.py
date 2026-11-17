#!/usr/bin/env python3
"""A word to type is sometimes a VALUE THE PAGE STATES, and sometimes a value nothing states.

THE MEASURED WALL
-----------------
`type_candidates` proposes text the page already contains: quoted spans, words of the
instruction, then any text on the page. Measured 2026-11-17 on `simple-arithmetic` -- the page
whose instruction is "Solve the math problem and type your answer into the textbox" and whose
only page text is `8 + 3 =` -- that generator offers 16 candidates in tiers 0..3 and the answer,
`11`, is among none of them, at any tier. It cannot be: `11` appears nowhere on the page. The
page states its OPERANDS and its OPERATOR and expects the value that follows from them.

So a page whose answer is a computed value is not a page the search fails on for want of budget.
Four arms on that page -- baseline, a learned prior, a page-local oracle prior, and a shuffled
control -- each spent exactly 1200 actions and none succeeded, while a hand call typing `11` and
pressing Submit succeeded on the first try. The wall is the candidate set, not the search.

THE SMALLEST THING THAT IS NOT A HARDCODED ANSWER
-------------------------------------------------
Two candidates, in this order:
  1  what the page already says, unchanged -- the existing generator, untouched;
  2  the ARITHMETIC the page itself spells out: `a op b` read from one element's own text,
     answered by the operator the tree already names (`+ - * /`).

This is not a lookup table of answers and it is not a language model. It reads two numbers and
one symbol that the page printed and applies the operation the symbol names. On
`simple-arithmetic` at seed 1060 the page prints `8 + 3 =` and the derived candidate is `11`;
at seed 1061 it might print `4 * 7 =` and the derived candidate is `28`. Nothing about the
answer is stored here; only the reading of `+ - * /` is.

WHY THIS IS THE RIGHT SHAPE AND NOT AN ARITHMETIC MODULE
--------------------------------------------------------
The defect is general: a candidate generator that can only COPY can never produce a value the
page did not already spell out. Arithmetic is the case this substrate actually contains, so it
is the case that can be measured today. The general statement, which the next probe should
attack, is that a typed value may be a FUNCTION of what the page states -- and the tree already
has the machinery for that in `value_algebra_v1` (typed operators that compose, so the answer
space is the product of the primitives rather than their sum) and `acquired_operator_memory_v1`
(an operator induced from worked examples, not named by a human). This module deliberately does
NOT import them yet: it does the smallest honest thing that removes the wall, so that the wall's
removal can be measured before a larger mechanism is trusted.

REFUSALS ARE PART OF IT
-----------------------
A page that prints `8 + 3 =` but where the instruction asks for something else is not evidence
to type `11`. The function returns the candidate and the reading it came from, so a caller can
rank it, price it, and discard it; it never types anything by itself and never claims the answer
is right. The verdict remains the page's own reward.

Authority: NONE. Producer-run sandbox measurement. No capability, weight or terminal credit.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DERIVED_TEXT_CANDIDATE_V1"

#: The operations a page can spell with one symbol. Read, not guessed: the symbol is ON the page.
OPERATORS: dict[str, Any] = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "×": lambda a, b: a * b,
    "x": lambda a, b: a * b,
    "/": lambda a, b: (a / b) if b else None,
    "÷": lambda a, b: (a / b) if b else None,
}

#: `8 + 3 =`, `12 x 4=`, `7 - 2 =`. The trailing `=` is what makes this a QUESTION rather than a
#: statement: a page that writes `8 + 3` without asking for the result is not asking anything.
_SPELLED = re.compile(
    r"(?P<a>-?\d+(?:\.\d+)?)\s*(?P<op>[+\-*×x/÷])\s*(?P<b>-?\d+(?:\.\d+)?)\s*=",
)


def _as_text(value: Any) -> str:
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def _page_texts(observation: Mapping[str, Any]) -> list[tuple[int | None, str]]:
    """Every string the page itself shows, with the element it came from when there is one."""
    out: list[tuple[int | None, str]] = []
    for element in observation.get("elements") or []:
        if not isinstance(element, Mapping):
            continue
        index = element.get("index")
        for name in ("text", "full_text", "value", "id"):
            value = element.get(name)
            if isinstance(value, str) and value:
                out.append((int(index) if isinstance(index, int) else None, value))
    for name in ("utterance", "instruction"):
        value = observation.get(name)
        if isinstance(value, str) and value:
            out.append((None, value))
    return out


def spelled(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every arithmetic question the page spells, and the value that answers it.

    Returned in page order so a caller's preference is the page's own order, not this module's.
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, text in _page_texts(observation):
        for match in _SPELLED.finditer(text):
            operator = match.group("op")
            operation = OPERATORS.get(operator)
            if operation is None:
                continue
            try:
                a, b = float(match.group("a")), float(match.group("b"))
            except ValueError:
                continue
            value = operation(a, b)
            if value is None:
                continue
            answer = _as_text(value)
            if answer in seen:
                continue
            seen.add(answer)
            found.append({"text": answer, "reading": match.group(0).strip(),
                          "operator": operator, "operands": [a, b], "from_element": index,
                          "source": text})
    return found


def candidates(observation: Mapping[str, Any], *,
               existing: Sequence[str] = ()) -> list[str]:
    """What a caller may try typing, the page's own text first and the derived value after.

    `existing` is whatever the current generator already offers; it is preserved exactly, in its
    own order, because a derived value must never displace a value the page stated.
    """
    out = list(dict.fromkeys(str(x) for x in existing))
    for row in spelled(observation):
        if row["text"] not in out:
            out.append(row["text"])
    return out


def describe(observation: Mapping[str, Any], *, existing: Sequence[str] = ()) -> dict[str, Any]:
    """The measurement a receipt can quote: what was spelled, what was derived, what was new."""
    rows = spelled(observation)
    offered = list(dict.fromkeys(str(x) for x in existing))
    added = [r for r in rows if r["text"] not in offered]
    return {"schema": SCHEMA, "authority": "NONE",
            "spelled": rows, "derived": [r["text"] for r in added],
            "existing_offered": len(offered), "added": len(added),
            "unchanged_when_nothing_spelled": not added}
