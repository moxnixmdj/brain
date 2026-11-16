"""Resolve "the blue triangle" when nothing on the page is called "the blue triangle".

The defect this closes, measured not guessed
--------------------------------------------
On 2026-11-16 the zero-experience instruction arm was measured on 130 real MiniWoB++ pages in a
real chromium substrate: 39 solved (0.300), and **51 pages refused with a typed reason**. The
refusal census was:

    16  REFUSED__SPATIAL_NEEDS_GEOMETRY           "drag the smaller box inside the larger box"
    12  REFUSED__NO_CLAUSE_UNDERSTOOD              "click on a black colored box"
    12  REFUSED__MULTI_APP_STATE_OUTSIDE_OBSERVATION
     4  REFUSED__LABEL_NOT_ON_THE_PAGE
     3  REFUSED__STYLE_NOT_IN_OBSERVATION          "give the text underlined style"
     2  REFUSED__VISUAL_QUANTITY_NEEDS_PIXELS

Then the pages were dumped. In **all 16** of the spatial refusals and **all 12** of the
no-clause ones, the target was described by an attribute the observation ALREADY CARRIES:

    "Click on the black colored box."   -> 4 divs, each with `colour`, one of them 'black'
    "Click on a triangle"               -> polygon/rect/circle tags plus a magenta fill
    "Drag the smaller box ..."          -> two `ui-draggable` boxes, 28x28 and 58x58
    "Drag all triangles into the black box." -> 3 polygons + 1 rect, the black one is the bin
    "Draw the number 8 in the checkboxes"    -> a 4x7 lattice of inputs plus an example <img>

So the compiler was not short of a *capability*. It was short of a *vocabulary*: it had a fixed
list of operators (CLICK_NAMED, SET_CONTROL, PRESS_SEQUENCE_BY_INDEX, ...) and any instruction
whose selector was not on that list was refused. That is the "knowledge house" failure at the
level of a program instead of in weights -- and it is worse, because a name that is absent from
the observation (a calendar) and a name that is merely absent from my operator list look
identical in the refusal census. They are not the same problem and they do not have the same fix.

What this module is
-------------------
A **version space over the observation's own dimensions**, which is the same machinery the
project already proved for learning, pointed at *looking* instead of at *acting*.

A description in words ("the smaller box", "the black box", "all triangles") is not matched by a
name. It is split into **discriminating predicates over dimensions the bridge already reports**:

    SIZE       relative: "the smaller" / "the larger"  -> order by box area, pick by rank
    COLOUR     "black", "blue"                         -> the element's own fill
    SHAPE      "triangle", "circle", "rect"            -> the tag / SVG element name
    CLASS      "the active side"                       -> the word is already a class
    COUNT      "how many"                              -> a count of the matched set
    RANK       "1st position", "the 2nd"               -> ordinal among siblings by geometry
    ALIGN      "top left", "bottom right"              -> which corner of the container

Every predicate is *decidable from the observation and nothing else*: no model, no pixels, no
network, no reward, no learned bytes (`K3 = 0`).

The three laws this is built on, each already proved elsewhere in this tree
--------------------------------------------------------------------------
1. **FILTER THEN PICK, NEVER PICK THEN FILTER** (measured on the 130 pages). "Click on a
   triangle" must restrict to the polygons FIRST and then choose; an implementation that picks
   the first pressable element and checks whether it happens to be a triangle fails on every page
   where the triangle is not first. The predicate defines a SET; the action chooses from the set.

2. **A DESCRIPTION THAT MATCHES MORE THAN ONE THING IS RESOLVED BY THE INSTRUCTION, NOT BY LUCK.**
   "the smaller box" is a comparison, not a colour: it is only decidable against the OTHER boxes
   on the page, so the predicate carries the whole candidate set and a rank. When two candidates
   remain tied the correct answer is AMBIGUOUS, never the first one -- picking the first is how a
   guess gets reported as a success.

3. **WHAT THE OBSERVATION CANNOT SUPPLY IS STILL REFUSED, BY NAME.** `colour` is absent from a
   plain HTML element that is coloured by a stylesheet; `tag` cannot distinguish "a triangle" from
   "a quadrilateral" when the page uses one `polygon` element for both. The residue stays refused
   with `ABSENT__<DIMENSION>`, because the difference between "I cannot express it" and "it is not
   there" is the whole distinction this module exists to maintain. A false pass is worse than a
   refusal: the wall diagnosis in `WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json` collapsed 3 pages
   into "budget" precisely by not keeping that distinction.

The interface
-------------
    describe("the smaller box", observation)  ->  Descriptor(subject, predicates, candidates, ...)

`candidates` is the resolved SET of element indices, ordered when the words imply an order.
An empty set with a missing dimension is `AMBIGUOUS`/`ABSENT__*`, never a silent `[]`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OBSERVABLE_DESCRIPTOR_V1"

# --- outcomes ------------------------------------------------------------------------------- #
RESOLVED = "RESOLVED__ONE_SUBJECT"          # exactly one element satisfies the description
RESOLVED_SET = "RESOLVED__A_SET"            # the instruction says "all", so the set is the answer
AMBIGUOUS = "AMBIGUOUS__MORE_THAN_ONE_MATCHES"   # the evidence does not separate them
ABSENT = "ABSENT__THE_OBSERVATION_HAS_NO_SUCH_DIMENSION"
NOTHING = "NOTHING__NO_ELEMENT_SATISFIES_THE_DESCRIPTION"

#: Colour words the pages in `miniwob-plusplus` actually paint with, plus the CSS names that
#: appear in instruction text. Kept as a literal because a colour word is a word, not a fact about
#: the world: the element's own `colour` field is what decides, and a page that paints with a
#: hex value simply will not match a name -- which is `NOTHING`, correctly, not a guess.
COLOUR_WORDS = frozenset({
    "black", "white", "grey", "gray", "red", "orange", "yellow", "green", "blue", "purple",
    "pink", "brown", "cyan", "magenta", "aqua", "lime", "navy", "teal", "olive", "maroon",
    "silver", "gold", "violet", "indigo", "turquoise", "beige", "crimson", "coral",
})

#: Shape words -> the SVG/HTML tags that can carry them. This is deliberately NOT a synonym list:
#: a `polygon` is used by these pages for both triangles and quadrilaterals, and on that page the
#: word "triangle" is genuinely undecidable from the tag. It is listed anyway because every page
#: that says "triangle" and paints with a `polygon` also distinguishes the alternatives by tag
#: (`rect`, `circle`), so the candidate set is still correct and the tie is reported as a tie.
SHAPE_TAGS = {
    "triangle": ("polygon",),
    "polygon": ("polygon",),
    "rect": ("rect",),
    "rectangle": ("rect",),
    "square": ("rect",),
    "box": ("div", "rect", "section", "article", "ul", "table"),
    "circle": ("circle",),
    "side": ("polygon", "rect", "circle"),
}

#: A role word -> the tags that can carry it. Unlike SHAPE_TAGS these are not shapes: "box" on
#: these pages is a `div` frame or a `rect`; "button" is a `button` or an `<a>`; "item" is whatever
#: the page lists.
KIND_TAGS = {
    "box": ("div", "rect", "section", "article"),
    "button": ("button", "a", "input"),
    "item": ("div", "span", "li", "rect", "circle", "polygon"),
    "checkboxes": ("input",),
    "checkbox": ("input",),
    "textbox": ("input", "textarea"),
    "text": ("text", "span", "p"),
}

SIZE_WORDS = {"smaller": -1, "larger": 1, "bigger": 1, "smallest": -1, "largest": 1}
ORDINAL_WORDS = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "first": 1, "second": 2,
                 "third": 3, "fourth": 4, "fifth": 5}
ALIGN_WORDS = ("top", "bottom", "left", "right", "middle", "center")

#: Words that name a *container/role* rather than a visual property. These are not resolved here:
#: they belong to the contract language, and `describe` returns them in `residual_words` so the
#: caller can see exactly what it still has to understand.
STOP_WORDS = frozenset({
    "a", "an", "the", "on", "in", "into", "to", "of", "with", "all", "every", "each", "that",
    "this", "is", "are", "and", "then", "press", "click", "drag", "move", "drop", "select",
    "hover", "type", "enter", "submit", "please", "now", "completely", "inside", "so", "it",
    "them", "its", "your", "you", "one", "colored", "coloured", "color", "colour",
    # NOTE: "box", "item", "button", "shape", "number" are deliberately NOT stop words. On these
    # pages they are often the only thing that names the kind of element (a `div` coloured box, a
    # `span` carrying an icon), so deleting them deletes the evidence. They simply fail to match
    # when there is nothing for them to match against, and that shows up as a residual word.
    "shape", "number", "numbers", "side",
})


@dataclass
class Descriptor:
    """The resolved meaning of a description, with the evidence for it and nothing else."""

    text: str
    outcome: str
    subject: int | None = None
    members: list[int] = field(default_factory=list)
    predicates: list[dict[str, Any]] = field(default_factory=list)
    residual_words: list[str] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)
    binds_relative_to: str | None = None      # "smaller"/"larger": a comparison, not a property
    schema: str = SCHEMA

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "text": self.text, "outcome": self.outcome,
            "subject": self.subject, "members": self.members,
            "predicates": self.predicates, "residual_words": self.residual_words,
            "missing_dimensions": self.missing_dimensions,
            "binds_relative_to": self.binds_relative_to,
        }


# --------------------------------------------------------------------------------------------- #
# reading the observation
# --------------------------------------------------------------------------------------------- #
def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def area(element: Mapping[str, Any]) -> int:
    box = element.get("box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return 0
    return int(box[2]) * int(box[3])


def _centre(element: Mapping[str, Any]) -> tuple[float, float] | None:
    box = element.get("box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    return float(box[0]) + float(box[2]) / 2.0, float(box[1]) + float(box[3]) / 2.0


def _contained(inner: Mapping[str, Any], outer: Mapping[str, Any]) -> bool:
    a, b = inner.get("box"), outer.get("box")
    if not (isinstance(a, (list, tuple)) and isinstance(b, (list, tuple))
            and len(a) == 4 and len(b) == 4):
        return False
    return (a[0] >= b[0] and a[1] >= b[1]
            and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3])


def _acting(elements: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """What the hand can actually address. Never guess about an element it cannot reach."""
    return [e for e in elements if e.get("can_click") or e.get("can_type")]


# --------------------------------------------------------------------------------------------- #
# the discriminators: each returns (surviving indices, predicate record) or None if not applicable
# --------------------------------------------------------------------------------------------- #
def _by_colour(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    if word not in COLOUR_WORDS:
        return None
    kept, missing, present = [], 0, 0
    for e in candidates:
        value = str(e.get("colour") or "").strip().lower()
        if not value:
            missing += 1
        else:
            present += 1
        if value and (value == word or value.startswith(word)):
            kept.append(int(e["index"]))
    record = {"dimension": "colour", "word": word, "matched": len(kept),
              "absent_on": missing}
    # Measured 2026-11-16 on drag-shapes: the instruction says "the black box" and the element it
    # means -- the bin at 80x45 -- carries NO colour at all, because its fill comes from the page's
    # stylesheet and the bridge reads only the element itself. The other shapes DO carry colour, so
    # a filter here would delete the right answer and report NOTHING. The honest reading is that the
    # page does not state this dimension: report it ABSENT and keep the candidates.
    if not kept and present < len(candidates):
        return None
    return kept, record


def _singular(word: str) -> str:
    """Pages say "all triangles" and the tag is one polygon. Morphology is not a dimension."""
    if word.endswith("es") and word[:-2] in SHAPE_TAGS:
        return word[:-2]
    if word.endswith("s") and word[:-1] in SHAPE_TAGS:
        return word[:-1]
    return word


def _by_shape(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    wanted = SHAPE_TAGS.get(_singular(word))
    if wanted is None:
        return None
    kept = [int(e["index"]) for e in candidates if str(e.get("tag") or "").lower() in wanted]
    return kept, {"dimension": "shape", "word": word, "tags": list(wanted), "matched": len(kept)}


def _by_class_word(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    """A word that is already a CSS class is evidence: the page itself says it."""
    if len(word) < 3:
        return None
    kept = [int(e["index"]) for e in candidates
            if word in str(e.get("classes") or "").lower()]
    if not kept:
        return None
    return kept, {"dimension": "class", "word": word, "matched": len(kept)}


def _by_element_kind(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    """ "box" / "button" / "the item": a KIND word, which keeps only what is of that kind.

    A kind word is the weakest discriminator and is applied only when nothing more specific can be
    (see the order in `describe`): it narrows without pretending to identify.
    """
    wanted = KIND_TAGS.get(word)
    if wanted is None:
        return None
    kept = [int(e["index"]) for e in candidates if str(e.get("tag") or "").lower() in wanted]
    if not kept:
        return None
    return kept, {"dimension": "kind", "word": word, "matched": len(kept),
                  "tags": list(wanted)}


def _by_size_rank(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    """A comparison against the OTHER candidates -- never an absolute size threshold."""
    direction = SIZE_WORDS.get(word)
    if direction is None:
        return None
    # Measured 2026-11-16: the page's own frame (480x210) is bigger than every named thing and
    # then wins "the larger box" every time. A candidate for a comparison must be of the same
    # order as the others -- within 8x of the median area -- or the comparison is being decided by
    # the page frame rather than by the instruction.
    boxes = sorted(area(e) for e in candidates if area(e) > 0)
    if len(boxes) < 2:
        sized = [e for e in candidates if area(e) > 0]
    else:
        median = boxes[len(boxes) // 2]
        sized = [e for e in candidates if 0 < area(e) <= 8 * max(median, 1)]
    if len(sized) < 2:
        return [], {"dimension": "size", "word": word, "matched": 0,
                    "why": "A_COMPARISON_NEEDS_SOMETHING_TO_COMPARE_AGAINST"}
    ranked = sorted(sized, key=area, reverse=(direction > 0))
    top = area(ranked[0])
    tied = [e for e in ranked if area(e) == top]
    kept = [int(e["index"]) for e in tied]
    return kept, {"dimension": "size", "word": word, "matched": len(kept),
                  "chosen_area": top, "compared_against": len(sized),
                  "tie": len(tied) > 1}


def _by_alignment(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    """ "the left box" / "the bottom right": a position relative to the OTHER candidates.

    Only meaningful when there are at least two candidates and they actually differ along the
    named axis. With one candidate the word is satisfied by everything and says nothing, so it is
    not evidence and must not be recorded as a predicate.
    """
    if word not in ALIGN_WORDS:
        return None
    if len(candidates) < 2:
        return None
    centres = [(int(e["index"]), _centre(e)) for e in candidates]
    centres = [(i, c) for i, c in centres if c is not None]
    if len(centres) < 2:
        return None
    xs = [c[0] for _, c in centres]
    ys = [c[1] for _, c in centres]
    if word in ("left", "right"):
        if max(xs) == min(xs):
            return None
        pick = min(xs) if word in ("left",) else max(xs)
        kept = [i for i, c in centres if c[0] == pick]
    elif word in ("top", "bottom"):
        if max(ys) == min(ys):
            return None
        pick = min(ys) if word == "top" else max(ys)
        kept = [i for i, c in centres if c[1] == pick]
    else:                                   # middle / center
        mx = (max(xs) + min(xs)) / 2.0
        kept = [i for i, c in centres if c[0] == min(xs, key=lambda x: abs(x - mx))]
    return kept, {"dimension": "alignment", "word": word, "matched": len(kept)}


def _by_ordinal_position(candidates, word) -> tuple[list[int], dict[str, Any]] | None:
    """The n-th of a vertical group, ordered by geometry -- the page's reading order."""
    n = ORDINAL_WORDS.get(word)
    if n is None:
        return None
    positioned = [e for e in candidates if _centre(e) is not None]
    if len(positioned) < n:
        return [], {"dimension": "rank", "word": word, "matched": 0}
    ordered = sorted(positioned, key=lambda e: (_centre(e)[1], _centre(e)[0]))
    chosen = ordered[n - 1]
    return [int(chosen["index"])], {"dimension": "rank", "word": word, "n": n,
                                    "among": len(ordered), "matched": 1}


# --------------------------------------------------------------------------------------------- #
# the resolver
# --------------------------------------------------------------------------------------------- #
def describe(text: str, observation: Mapping[str, Any], *,
             pool: Iterable[int] | None = None) -> Descriptor:
    """Resolve a description to the element(s) it names, or say precisely why it cannot.

    `pool` restricts the candidate set (a bin of a drag task, the checkboxes of a lattice). It is
    applied BEFORE every predicate: see law 1 at the top of this file.
    """
    elements = list(observation.get("elements") or [])
    by_index = {int(e["index"]): e for e in elements}
    candidates = ([by_index[i] for i in pool if i in by_index] if pool is not None
                  else _acting(elements))

    words = _words(text)
    predicates: list[dict[str, Any]] = []
    residual: list[str] = []
    missing: list[str] = []
    relative: str | None = None
    is_set = bool({"all", "every", "each"} & set(words))
    working = list(candidates)

    for word in words:
        if word in STOP_WORDS:
            continue
        applied = None
        for discriminator in (_by_colour, _by_shape, _by_size_rank, _by_alignment,
                              _by_ordinal_position):
            got = discriminator(working, word)
            if got is not None:
                applied = got
                break
        if applied is None:
            applied = _by_class_word(working, word)
        if applied is None:
            applied = _by_element_kind(working, word)
        if applied is None:
            residual.append(word)
            if word in COLOUR_WORDS:
                missing.append("COLOUR__THE_BRIDGE_READS_ONLY_THE_ELEMENTS_OWN_FILL_AND_PAGES_"
                               "PAINT_WITH_A_STYLESHEET")
            elif word.isdigit():
                missing.append("THE_LITERAL_IS_NOT_A_DIMENSION__IT_NAMES_CONTENT_THAT_IS_AN_IMAGE")
            continue
        kept, record = applied
        predicates.append(record)
        if word in SIZE_WORDS:
            relative = word
        # FILTER: a predicate that matches nothing means the description does not fit this pool.
        if not kept:
            return Descriptor(text=text, outcome=NOTHING, predicates=predicates,
                              residual_words=residual, missing_dimensions=sorted(set(missing)),
                              binds_relative_to=relative)
        working = [by_index[i] for i in kept if i in by_index]

    # A KIND word is the weakest evidence there is: apply it only when nothing else narrowed at all.
    if not predicates:
        for word in list(residual):
            got = _by_element_kind(working, word)
            if got is not None:
                kept, record = got
                residual.remove(word)
                predicates.append(record)
                working = [by_index[i] for i in kept if i in by_index]
                break

    if not predicates:
        missing = []
        if any(w in COLOUR_WORDS for w in residual):
            missing.append("COLOUR__THE_BRIDGE_READS_ONLY_THE_ELEMENTS_OWN_FILL_AND_PAGES_PAINT_WITH_A_STYLESHEET")
        if any(w.isdigit() for w in residual):
            missing.append("THE_LITERAL_IS_NOT_A_DIMENSION__IT_NAMES_A_CONTENT_THAT_IS_AN_IMAGE")
        if not missing:
            missing.append("THE_DESCRIPTION_NAMES_NO_OBSERVABLE_DIMENSION")
        return Descriptor(text=text, outcome=ABSENT, predicates=predicates,
                          residual_words=residual, missing_dimensions=missing)

    members = [int(e["index"]) for e in working]
    if is_set and members:
        return Descriptor(text=text, outcome=RESOLVED_SET, members=members,
                          predicates=predicates, residual_words=residual,
                          missing_dimensions=sorted(set(missing)),
                          binds_relative_to=relative)
    if len(members) == 1:
        return Descriptor(text=text, outcome=RESOLVED, subject=members[0], members=members,
                          predicates=predicates, residual_words=residual,
                          missing_dimensions=sorted(set(missing)),
                          binds_relative_to=relative)
    return Descriptor(text=text, outcome=AMBIGUOUS, members=members, predicates=predicates,
                      residual_words=residual, missing_dimensions=sorted(set(missing)),
                      binds_relative_to=relative)


def container_of(observation: Mapping[str, Any], inner: int | None = None) -> dict[str, Any]:
    """Which element is the thing you drag INTO.

    Two pieces of evidence are used, in order, and both are the page's own words:

      DRAGGABLE_ASYMMETRY  some elements are marked draggable and one big one is not
      FILL_ASYMMETRY      the items carry a fill and one big element carries none

    Everything else is reported as no-evidence rather than guessed. Measured 2026-11-16: on
    drag-shapes the bin is element 8, a `rect` 80x45 with NO colour while every shape around it
    has one -- but the shapes are NOT inside it, so a containment test (the obvious first
    implementation) finds nothing at all. On drag-box neither asymmetry holds and the target is
    named by a size comparison instead, which `describe` already resolves; refusing here is the
    correct answer on that page, not a gap.
    """
    elements = list(observation.get("elements") or [])
    # A drop target is something the hand can address and that is not the submit control: pressing
    # submit ends the episode, so it is never a place to put something. Excluding it by what it says
    # (not by an index) keeps that true on every page.
    usable = [e for e in elements
              if area(e) > 0 and int(e["index"]) != inner
              and (e.get("can_click") or e.get("can_type"))
              and str(e.get("tag") or "").lower() not in ("button", "input")
              and str(e.get("text") or "").strip().lower() not in ("submit", "ok", "done", "close")]
    if not usable:
        return {"outcome": "NOTHING__NO_ELEMENT_HAS_A_BOX", "target": None, "evidence": None}
    biggest = max(usable, key=area)
    if area(biggest) <= 0:
        return {"outcome": "NOTHING__NO_ELEMENT_HAS_A_BOX", "target": None, "evidence": None}

    draggable = [e for e in usable if "draggable" in str(e.get("classes") or "").lower()]
    if draggable and biggest not in draggable:
        return {"outcome": RESOLVED, "target": int(biggest["index"]),
                "evidence": "DRAGGABLE_ASYMMETRY",
                "items": [int(e["index"]) for e in draggable]}

    filled = [e for e in usable if e.get("colour")]
    # A target is an UNFILLED region at least twice the size of every item. Measured 2026-11-16 on
    # drag-shapes-2: two unfilled 70x50 boxes and five 17x17 shapes -- ambiguity is the honest answer
    # there, and the instruction's own words ("the left box") decide between them, not this function.
    targets = [e for e in usable
               if not e.get("colour") and filled
               and area(e) >= 2 * max(area(x) for x in filled)]
    if len(targets) == 1:
        return {"outcome": RESOLVED, "target": int(targets[0]["index"]),
                "evidence": "FILL_ASYMMETRY", "items": [int(e["index"]) for e in filled]}
    if len(targets) > 1:
        return {"outcome": AMBIGUOUS, "target": None, "evidence": "FILL_ASYMMETRY",
                "candidates": [int(e["index"]) for e in targets],
                "items": [int(e["index"]) for e in filled]}

    return {"outcome": "ABSENT__NO_EVIDENCE_NAMES_A_TARGET", "target": None, "evidence": None,
            "considered": int(biggest["index"])}


def spatial_relation(observation: Mapping[str, Any], subject: int | None,
                     target: int | None) -> dict[str, Any]:
    """The words are checked against the boxes, not assumed.

    Returns the direction the hand must travel, computed from the two centres, so a drag is
    decided by geometry rather than by a guess about which way "into" points.
    """
    elements = {int(e["index"]): e for e in observation.get("elements") or []}
    if subject not in elements or target not in elements:
        return {"relation": "UNDECIDABLE__THE_TWO_THINGS_ARE_NOT_BOTH_PRESENT"}
    a, b = _centre(elements[subject]), _centre(elements[target])
    if a is None or b is None:
        return {"relation": "ABSENT__BOX"}
    already = _contained(elements[subject], elements[target])
    return {"relation": "ALREADY_SATISFIED" if already else "MUST_MOVE",
            "dx": round(b[0] - a[0], 1), "dy": round(b[1] - a[1], 1),
            "subject": subject, "target": target}
