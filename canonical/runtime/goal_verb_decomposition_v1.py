"""Read the verb, not the sentence.

THE FAILURE THIS REPLACES
-------------------------
r130/r131 measured this project's reach on unselected MiniWob++ samples: 6/60 and
5/40. The dominant failure was not perception, not resolution and not learning --
28 of 40 tasks were never ATTEMPTED. The policy matched five hand-written goal
shapes and MinimWob has dozens.

Reading all 130 task files showed why that was the wrong shape of solution. The
goals are not infinitely varied. They share one structure:

    VERB  <operand>

with about sixteen verbs in total (click, enter, type, select, drag, draw, find,
highlight, scroll, focus, copy, set, sort, push, switch, move, expand) and an
operand that is one of a small number of kinds (a quoted token, an ordinal, a
colour, a coordinate, a number, a direction, a repeated item). Forty-five
sentence patterns collapse to sixteen verbs times a handful of operand kinds.

A policy that hard-codes sentence patterns has coverage proportional to how many
patterns somebody wrote. A policy that parses verb and operand has coverage
proportional to how many VERBS it implements, and verbs are what the environment
actually offers. That is the difference between 30% and something worth measuring.

WHAT THIS MODULE DOES
---------------------
It is pure: text in, plan out. No browser, no environment. It answers one
question -- "what verb is this goal asking for, and what is the operand" -- and
returns a plan carrying the primitive the runner should use. It never invents a
verb it does not implement; an unrecognised goal returns UNSUPPORTED_VERB with
the verb it saw, so coverage gaps are counted rather than hidden behind a
generic click.

THE HONEST LIMIT
----------------
Parsing the verb does not make the verb work. `draw-line` needs a freehand
stroke, `simon-says` needs memory, `bisect-angle` needs geometry. A verb plan
raises COVERAGE, which is the factor this project measured at 30%; it does not
raise the success rate within a verb, which was already 5/12 among attempted
tasks. Both numbers must be reported separately or the improvement is fake.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GOAL_VERB_DECOMPOSITION_V1"

# (verb, regex on the lowered goal). Order matters: more specific first.
# VERB PATTERNS: written as AFFORDANCES, not as the benchmark's sentences.
#
# r141 measured what the old table was worth. Ten of nineteen paraphrases of goals the
# system passes every time produced verb=None -- total refusal:
#     "Press the button."                  refused   ("click" only)
#     "Hit the button."                    refused
#     "Rotate the cube so that 4 faces..." refused   ("move the cube around" only)
#     "Press the buttons in the order..."  refused   ("push the buttons..." only)
# That is the difference between storing a CLASS and storing a STRING. A human who has
# clicked a button once can act on "press", "hit", "tap" and "activate", because what they
# stored is "direct the pointing device at the control", not the sentence.
#
# So each verb now lists the verbs a person would accept for the same affordance, and the
# specific-before-general order is preserved. The patterns are still the same kind of
# object; what changed is that they describe the ACT rather than one phrasing of it.
VERB_PATTERNS = (
    # A QUESTION IS A VERB. "How many small Qs are there?" contains none of the action
    # words below, so it was refused before the page was ever read -- and the page is
    # where the answer is. This goes FIRST because a counting question often also
    # contains an action word ("how many green items ..."). Measured 2026-11-09 on
    # count-shape, 0/30.
    ("COUNT", r"\bhow many\b|\bcount the\b|\bwhat (?:is|are) the number of\b"),
    ("SET_SLIDERS", r"\bset the sliders?\b|\b(adjust|move) the sliders?\b"),
    ("SORT", r"\bsort\b|\border the (numbers|items)\b"),
    ("PUSH_SEQUENCE", r"\b(push|press|hit|tap|click|repeat|enter)\b.*\b(sequence|order|shown|displayed|pattern)\b"),
    ("SIMON", r"\b(repeat|memorize|watch)\b.*\bsequence\b"),
    ("COPY_PASTE", r"\bcopy\b.*\bpaste\b"),
    ("FIND_AND_TYPE", r"\bfind\b.*\b(last|first)\b.*\bword\b"),
    ("SWITCH_TABS", r"\bswitch\b.*\btabs?\b|\bg(o|et) to the .{0,20}tab\b"),
    ("EXPAND_AND_CLICK", r"\bexpand\b|\bopen the (pie menu|section|accordion)\b"),
    ("HIGHLIGHT", r"\bhighlight\b|\bselect the text\b"),
    ("SCROLL_TO", r"\bscroll\b"),
    ("FOCUS", r"\bfocus\b|\bput the cursor\b|\bclick into\b"),
    ("DRAW", r"\bdraw\b|\bsketch\b|\btrace\b"),
    ("MOVE", r"\b(move|rotate|turn|spin)\b.*\b(cube|object|shape|item)\b|\b(cube|object)\b.*\b(rotate|turn)\b"),
    ("DRAG", r"\bdrag\b|\bdrop\b|\b(drag|move)\b.*\b(into|onto|around)\b"),
    ("ENTER", r"\b(enter|type|write|fill|input|put)\b"),
    ("SELECT", r"\bselect\b|\bchoose\b|\bpick\b"),
    ("FIND", r"\bfind\b|\blocate\b"),
    ("CLICK", r"\bclick\b|\bpress\b|\bhit\b|\btap\b|\bactivate\b|\bclick on\b|\bgo to\b"),
)


# A SLOT is a (field, value) pair the goal states and the page has a control for. This is
# the general form of "fill in the form": most real computer use is this, and MiniWob's
# fixed grammar hid it. Measured motivation: the Alaska flight page has fields named
# SearchFields.DepartureCity / ArrivalCity / DepartureDate / ReturnDate and the goal
# "Book a return flight from New York to Las Vegas, departing March 2 and returning
# March 24" decomposed to verb=None -- the pipeline had nothing to say on a page where
# every value and every field were plainly present.
SLOT_PATTERNS = (
    # A QUOTED REFERENCE IS A SLOT.
    #
    # The seven patterns below describe a flight-booking form: "from X to Y departing Z".
    # MiniWob is not that corpus. `Close the dialog box by clicking the "x".` states its
    # reference with quote marks and matched none of them, so slots() returned {} and the
    # no-verb fallback could never fire -- the sentence was refused as UNSUPPORTED_VERB
    # with its reference sitting in plain sight. This pattern is placed first and is the
    # only one whose shape is the markup of an instruction rather than the grammar of a
    # domain: the sentence tells you what to act on by quoting it.
    ("reference",   r'"([^"]{1,40})"'),
    ("reference",   r"\u201c([^\u201d]{1,40})\u201d"),
    ("reference",   r"'([^']{1,40})'"),
    # THE SENTENCES SAY `from: X` AND THE PATTERNS SAID `from X`.
    #
    # Measured 2026-11-09 against the live corpus: "Book the cheapest one-way flight
    # from: Kakhonak, AK to: Havasupai, AZ on 10/14/2016." matched NONE of the four
    # travel patterns, because each required `from ` followed immediately by a capital
    # letter and MiniWob writes `from:` with a colon. Three tasks (book-flight,
    # book-flight-nodelay, and their nodelay twin) were refused as unreadable while
    # every value they need sat in the sentence. The colon is optional below, and the
    # date pattern accepts the M/D/YYYY form the corpus actually uses.
    # A CITY NAME CONTAINS A SLASH. "Ventura/Oxnard, CA" matched none of the character
    # classes below and `origin` was silently skipped while destination and date filled.
    # The class now admits '/', which is what the corpus actually writes.
    ("origin",      r"\bfrom:?\s+([A-Z][\w .,'/\-]{1,30}?)(?=\s+to:?\b|\s*,|$)"),
    ("destination", r"\bto:?\s+([A-Z][\w .,'/\-]{1,30}?)(?=\s*(?:,|departing|returning|on\b|$))"),
    ("destination", r"\bto:?\s+([A-Z][\w .,'/\-]{1,30})"),
    ("depart",      r"\bdeparting\s+(?:on\s+)?([\w]+\s+\d{1,2}|\d{1,2}\s+[\w]+|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"),
    ("return",      r"\breturning\s+(?:on\s+)?([\w]+\s+\d{1,2}|\d{1,2}\s+[\w]+|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"),
    ("date",        r"\bon\s+([\w]+\s+\d{1,2}|\d{1,2}\s+[\w]+|\d{1,2}/\d{1,2}/\d{4})"),
    ("amount",      r"\b(?:amount|total|price)\s+(?:of\s+)?([\d.,]+)"),
    ("email",       r"([\w.+-]+@[\w-]+\.[\w.]+)"),
    # THE SENTENCE STATES ITS FIELDS IN THE SAME ORDER THE FORM OFFERS THEM.
    #
    # Measured 2026-11-09 on `multi-layouts` and `multi-orderings`: the goal is
    # "Search for horror movies directed by Michael from year 1982." and the page is
    # three anonymous <input type=text> with no id, no placeholder and no label in the
    # rendered layout. Nothing on the page says which box is which, so role-by-name
    # binding cannot work and reported UNSUPPORTED_VERB instead. The sentence supplies
    # three references in order and the form offers three boxes in order; the task's own
    # source declares them in exactly that order (genreBox, nameBox, yearBox).
    ("genre",       r"\b(?:for|about)\s+(\w+)\s+(?:movies?|films?)\b"),
    ("director",    r"\bdirected\s+by\s+([A-Z][\w'-]{1,20})"),
    ("year",        r"\bfrom\s+year\s+(\d{4})"),
)


def slots(text: str) -> dict[str, str]:
    """Everything the instruction states as a (role, value) pair.

    This is deliberately a READER, not a planner: it says what the sentence supplies, and
    leaves the decision of which control receives it to the resolver. A slot the page has no
    control for is simply unused, which is why a sentence with extra words still works.
    """
    out: dict[str, str] = {}
    for role, pattern in SLOT_PATTERNS:
        if role in out:
            continue
        m = re.search(pattern, text)
        if m:
            out[role] = m.group(1).strip(" ,.")
    return out


def _number(text: str) -> int | None:
    m = re.search(r"(-?\d+)", text)
    return int(m.group(1)) if m else None


def _quoted(text: str) -> str | None:
    """The reference the sentence names, in any of the marks an instruction uses.

    Measured 2026-11-09: this read double quotes and curly quotes only. `Playing as 'X'`
    and `clicking the 'x'` were invisible to it, while `"x"` passed. Three of the public
    tasks that were blind for a whole round carry the token in single quotes.
    """
    for pat in ('"([^"]*)"', "\u201c([^\u201d]*)\u201d", "'([^']*)'",
                "\u2018([^\u2019]*)\u2019"):
        m = re.search(pat, text)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def _colour(text: str) -> str | None:
    """Colour words, from the one list this repo already keeps.

    This used to be an absolute package import (`from canonical.runtime import ...`) executed
    at call time. When the module is loaded from a file path -- which every measurement
    harness in this project does -- that import raises ModuleNotFoundError, the exception
    escapes decompose(), and the episode is recorded as a generic failure with no action
    attempted. That silently removed every colour-operand goal from r137 while leaving the
    other tasks intact, so the run looked like a capability loss and was really an import
    bug. The sibling import is now guarded and falls back to a local list.
    """
    try:
        from canonical.runtime import appearance_address_v1 as appearance   # noqa: PLC0415
        colours = appearance.COLOURS
    except Exception:
        colours = ("black", "white", "red", "green", "blue", "yellow", "olive",
                   "cyan", "magenta", "pink", "gray", "grey", "orange", "purple",
                   "brown", "navy", "teal", "silver", "lime", "maroon")
    for word in colours:
        if re.search(r"\b" + re.escape(word) + r"\b", text, re.I):
            return word
    return None


def _path(text: str) -> list[str] | None:
    """A>B>C nesting, as used by the menu tasks."""
    m = re.search(r"select\s+([^\s>]+(?:>[^\s>]+)+)", text, re.I)
    return [p.strip() for p in m.group(1).split(">")] if m else None


def decompose(goal: str) -> dict[str, Any]:
    """Return {verb, operand, plan} for a goal sentence, or an explicit refusal."""
    text = " ".join(str(goal or "").split())
    if not text:
        return {"schema": SCHEMA, "verb": None, "status": "EMPTY_GOAL", "plan": None}

    lowered = text.lower()
    verb = None
    for name, pattern in VERB_PATTERNS:
        if re.search(pattern, lowered):
            verb = name
            break
    if verb is None:
        found = slots(text)
        # A NAMED REFERENCE PLUS AN ACTING WORD IS A FIND, NOT A FORM.
        #
        # "Close the dialog box by clicking the \"x\"." supplies a reference and an action.
        # With only the FILL_FORM fallback it routed to the form filler, which looks for
        # input fields and finds none. FIND already means "resolve this reference on the
        # page and click it", which is what the sentence asks for; FILL_FORM means "put
        # these values into controls", which it does not. The discriminator is the verb
        # word in the sentence, not the presence of a reference.
        if found.get("reference") and re.search(
                r"\b(click|close|press|choose|select|pick|open|hit|tap)\b", lowered):
            return {"schema": SCHEMA, "verb": "FIND", "status": "DECOMPOSED",
                    "plan": "reference", "goal": text, "operand": {"token": found["reference"]}}
        if found:
            # No known verb, but the instruction names concrete values. That is a form fill,
            # and refusing it was the single largest measured blindness in this project: a
            # booking page with four named fields was answered with UNSUPPORTED_VERB.
            return {"schema": SCHEMA, "verb": "FILL_FORM", "status": "DECOMPOSED",
                    "plan": "slots", "goal": text, "operand": {"slots": found}}
        return {"schema": SCHEMA, "verb": None, "status": "UNSUPPORTED_VERB",
                "plan": None, "goal": text,
                "reason": "no known verb appears in this goal"}

    operand: dict[str, Any] = {}
    if verb in ("SET_SLIDERS",):
        operand["values"] = [int(x) for x in re.findall(r"-?\d+", text)]
    elif verb in ("DRAG", "MOVE", "SORT"):
        operand["quoted"] = _quoted(text)
        operand["number"] = _number(text)
    elif verb in ("SELECT",):
        operand["path"] = _path(text)
        if operand["path"] is None:
            m = re.search(r"select\s+(.+?)\s*(?:from the list|and click submit|$)", text, re.I)
            operand["token"] = m.group(1).strip() if m else None
        operand["colour"] = _colour(text)
    elif verb in ("ENTER", "FIND_AND_TYPE"):
        operand["token"] = _quoted(text)
        if operand["token"] is None:
            m = re.search(r"(?:enter|type)\s+([A-Za-z0-9_\-]+)", text, re.I)
            operand["token"] = m.group(1) if m else None
        operand["field"] = "textarea" if "textarea" in lowered else "text"
    elif verb in ("CLICK", "FIND", "HIGHLIGHT", "SCROLL_TO", "FOCUS", "EXPAND_AND_CLICK"):
        operand["quoted"] = _quoted(text)
        operand["colour"] = _colour(text)
        operand["number"] = _number(text)
        if operand["quoted"] is None:
            m = re.search(r"click on the\s+([a-z][a-z\- ]{2,20}?)\s+button", lowered)
            operand["button_word"] = m.group(1).strip() if m else None
    elif verb in ("DRAW",):
        operand["quoted"] = _quoted(text) or (str(_number(text)) if _number(text) is not None else None)
    elif verb in ("PUSH_SEQUENCE", "SIMON", "COPY_PASTE", "SWITCH_TABS"):
        operand["quoted"] = _quoted(text)
    elif verb in ("SCROLL_TO",):
        operand["quoted"] = _quoted(text)

    return {"schema": SCHEMA, "verb": verb, "status": "DECOMPOSED",
            "operand": operand, "goal": text}


def coverage_of(goals: list[str]) -> dict[str, Any]:
    """How many of these goals decompose at all, and to which verbs."""
    counts: dict[str, int] = {}
    unsupported = []
    for g in goals:
        d = decompose(g)
        if d["status"] == "DECOMPOSED":
            counts[d["verb"]] = counts.get(d["verb"], 0) + 1
        else:
            unsupported.append(g[:70])
    total = len(goals)
    covered = total - len(unsupported)
    return {"total": total, "covered": covered,
            "coverage": round(covered / total, 4) if total else 0.0,
            "by_verb": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "unsupported": unsupported}
