#!/usr/bin/env python3
"""THE BOTTLENECK WAS NOT THAT LEARNING IS WEAK. IT IS THAT ACTING AND LEARNING SPEAK DIFFERENTLY.

What was measured first (2026-11-16, from the recorded one-success run, no new episodes):

    one demonstration buys          ~1 bit   (it strikes out the descriptions that would have
                                             done something else there -- a binary question each)
    one step costs                  5.43 bits (median 51 descriptions still standing, max 255)
    steps needing >1 demonstration  174 of 175

So a single success cannot identify a program. That part is arithmetic and it is not new.

THE DEFECT, FOUND BY ASKING A DIFFERENT QUESTION
------------------------------------------------
The arithmetic above is only about the LEARNER. It became interesting when the same page was read
by the two halves of this system, because they do not share a vocabulary:

    acting   `instruction_policy_v1` -> `instruction_contract_v1` + `anchored_frame_v1`
             resolves the sentence to an ELEMENT INDEX on the page in front of it
    learning `demonstration_version_space_v1`
             has its own private grammar of ('equals','self','classes',...) tuples

They agree on nothing structural. The act half never sees a description tuple; the learned half
never sees a clause. So the 5.43 bits are spent identifying an element in a vocabulary that the
acting half does not consult -- and a skill can be perfectly learned and still unreachable, which is
the same "the capability existed, was verified, and could not be reached" failure this tree has
already paid for three times at other layers (a shell command that could not be bound, a tab the
reveal had no name for, a Submit the sentence never said).

Meanwhile the tree had already written the law down twice and not applied it here:

    instruction_policy_v1: "The planner resolves a clause to an element with the SAME functions the
    checker uses... Import, never re-derive."

    demonstration_version_space_v1: "A recorded success says WHAT was clicked... not WHY."

The same law is needed one level up: **the thing that acts and the thing that learns must describe
the element the same way.** Otherwise one bit of experience is written in a language nothing reads.

WHAT THIS MODULE IS
-------------------
`describe(element, observation)` -- ONE description of an element, from the observation alone, in a
form both halves can produce and consume:

    identity    the element's OWN words (text/value/aria/title/alt), never its subtree
    class/id    the page's own names
    structure   parent tag, previous/next sibling tag
    geometry    its box, because a page can be answered by position and only a box carries that

`identify(description, observation)` -- the inverse: the element(s) that description picks out. It
returns ALL of them, never the first, because "how many other elements would this description also
select" is exactly the price `what_one_experience_buys_v1` computes, and a resolver that silently
returns the first match cannot report it.

`bits(description, observation)` -- log2 of that count. That is the cost of the description, in the
same units the recorded run reports, so the two can be compared without conversion.

WHY THIS IS NOT A SECOND RESOLVER
---------------------------------
It adds no new way of deciding anything. `instruction_contract_v1` already decides WHICH element a
sentence names, and it keeps doing that. This module only writes down what was decided, in a form
that survives the page, so that a skill can be stored and re-read. It is a SIGNATURE, not a judge:
it never says an element is the right one, only which elements it is indistinguishable from.

AUTHORITY NONE. Pure function of (description, observation). No model, no reward, no parameters,
no state.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ONE_DESCRIPTION_LANGUAGE_V1"

#: The properties an element can be named by. Closed on purpose: an open list is a guess about which
#: attribute the page will use next, and this module must be able to say "nothing here names it".
OWN_WORDS = ("text", "value", "aria-label", "title", "alt")
PAGE_NAMES = ("id", "classes", "tag", "type", "role", "name", "placeholder", "for")


@dataclass(frozen=True)
class Description:
    """One element's description. Serializable, because it is meant to outlive the page."""
    own: str = ""            # the element's own words, normalised
    id: str = ""
    classes: tuple[str, ...] = ()
    tag: str = ""
    parent_tag: str = ""
    prev_tag: str = ""
    next_tag: str = ""
    box: tuple[int, int, int, int] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "own": self.own, "id": self.id, "classes": list(self.classes),
                "tag": self.tag, "parent_tag": self.parent_tag, "prev_tag": self.prev_tag,
                "next_tag": self.next_tag, "box": list(self.box) if self.box else None}

    def key(self) -> str:
        """A stable name, so a description can be stored as one line and compared as one string."""
        blob = json.dumps(self.as_dict(), sort_keys=True)
        return "ELEM_" + hashlib.sha256(blob.encode()).hexdigest()[:16]

    def strength(self) -> int:
        """How much of the element this description actually pins down (higher = more specific)."""
        return sum(1 for part in (self.own, self.id, " ".join(self.classes), self.tag,
                                  self.parent_tag, self.prev_tag, self.next_tag,
                                  self.box is not None) if part)


def _words(text: Any) -> str:
    return " ".join(str(text or "").split()).strip().lower()


def _tags(elements: Sequence[Mapping[str, Any]], index: int) -> tuple[str, str, str]:
    """(parent tag, previous sibling tag, next sibling tag), read from the parent links only."""
    by_index = {int(e.get("index", -1)): e for e in elements}
    if not (0 <= index < 10 ** 6) or index not in by_index:
        return "", "", ""
    element = by_index[index]
    parent = int(element.get("parent", -1))
    parent_tag = str(by_index[parent].get("tag") or "") if parent in by_index else ""
    siblings = [e for e in elements if int(e.get("parent", -2)) == parent]
    position = next((i for i, e in enumerate(siblings) if int(e.get("index", -1)) == index), None)
    prev_tag = str(siblings[position - 1].get("tag") or "") if position not in (None, 0) else ""
    next_tag = (str(siblings[position + 1].get("tag") or "")
                if position is not None and position + 1 < len(siblings) else "")
    return parent_tag, prev_tag, next_tag


def describe(element: Mapping[str, Any], observation: Mapping[str, Any]) -> Description:
    """One element's description, from the observation alone.

    IDENTITY COMES FROM THE ELEMENT'S OWN WORDS. `full_text` is subtree text and using it makes one
    record look like seven (measured elsewhere in this tree); it is deliberately not read here.
    """
    elements = list(observation.get("elements") or [])
    index = int(element.get("index", -1))
    own = next((_words(element.get(k)) for k in OWN_WORDS if _words(element.get(k))), "")
    parent_tag, prev_tag, next_tag = _tags(elements, index)
    box = element.get("box")
    return Description(
        own=own,
        id=str(element.get("id") or ""),
        classes=tuple(sorted(str(element.get("classes") or "").split())),
        tag=str(element.get("tag") or ""),
        parent_tag=parent_tag, prev_tag=prev_tag, next_tag=next_tag,
        box=tuple(int(x) for x in box[:4]) if isinstance(box, (list, tuple)) and len(box) >= 4
        else None)


def _matches(description: Description, element: Mapping[str, Any],
             observation: Mapping[str, Any], *, use: tuple[str, ...]) -> bool:
    """Whether this element is described by `description`, restricted to the named parts.

    `use` is what makes the count meaningful: the price of a description depends on WHICH of its
    parts are used, so the caller must be explicit. A description used in full is cheap and brittle;
    used by its id alone it is expensive and stable. Both are honest, and they cost differently.
    """
    own = next((_words(element.get(k)) for k in OWN_WORDS if _words(element.get(k))), "")
    if "own" in use and description.own and own != description.own:
        return False
    if "own" in use and not description.own and own:
        return False
    if "id" in use and str(element.get("id") or "") != description.id:
        return False
    if "classes" in use:
        if tuple(sorted(str(element.get("classes") or "").split())) != description.classes:
            return False
    if "tag" in use and str(element.get("tag") or "") != description.tag:
        return False
    if "box" in use:
        box = element.get("box")
        got = tuple(int(x) for x in box[:4]) if isinstance(box, (list, tuple)) and len(box) >= 4 else None
        if got != description.box:
            return False
    if "structure" in use:
        index = int(element.get("index", -1))
        parent_tag, prev_tag, next_tag = _tags(list(observation.get("elements") or []), index)
        if (parent_tag, prev_tag, next_tag) != (description.parent_tag, description.prev_tag,
                                                description.next_tag):
            return False
    return True


def ordinal(element: Mapping[str, Any], observation: Mapping[str, Any]) -> str:
    """Where the element sits among the elements its own description cannot separate.

    THE SECOND GAP, MEASURED 2026-11-16: 149 of 1415 actionable elements carry a name that appears
    more than once on the page ("duration:" on four labels). The observation already says which one
    it is -- their ORDER -- and `instruction_policy_v1` already reads position to name things
    ("the 5th word", "the 3rd checkbox"). Position is therefore not a new idea here; it is the tree's
    existing way of separating twins, and it costs log2(k) bits less than giving up on the name.

    1-based by document order of the SAME description. "0" is never returned: an element that the
    description already separates is the 1st of one.
    """
    peers = identify(describe(element, observation), observation)
    index = int(element.get("index", -1))
    return str(peers.index(index) + 1) if index in peers else "1"


def identify(description: Description, observation: Mapping[str, Any], *,
             use: tuple[str, ...] = ("own", "id", "classes", "tag"),
             ordinal: int | None = None) -> list[int]:
    """Every element this description picks out. ALL of them.

    A resolver that returns the first match cannot report its own ambiguity, and the ambiguity IS
    the price. This one returns the set, so `bits()` can be computed from it and a caller can refuse
    to act when the set has more than one member.
    """
    found = [int(e["index"]) for e in observation.get("elements") or []
             if _matches(description, e, observation, use=use)]
    # AN ORDINAL SEPARATES TWINS WITHOUT GIVING UP THE NAME. The peers are ordered by their place in
    # the observation, which is document order; asking for the 3rd returns the 3rd or nothing.
    if ordinal is not None and found:
        position = int(ordinal) - 1
        return [found[position]] if 0 <= position < len(found) else []
    return found


def peer_count(description: Description, observation: Mapping[str, Any]) -> int:
    """How many elements the description picks out here. An ordinal must be stored WITH this.

    MEASURED 2026-11-16 across five seeds on five pages: the peer-count is invariant for 229 of 241
    descriptions (95.0%) and changes for 12 -- all of them on `email-inbox`, where the number of
    rows differs per instance. So an ordinal is stable in the common case and NOT in general, and a
    stored ordinal that does not carry the count it was taken under cannot be checked when it is
    replayed. That check is the difference between a skill that refuses and a skill that answers the
    wrong element confidently.
    """
    return len(identify(description, observation))


def ordinal_is_valid(ordinal: int, expected_peer_count: int,
                     description: Description, observation: Mapping[str, Any]) -> bool:
    """Whether a stored (ordinal, peer-count) pair still means the same thing on this page."""
    if peer_count(description, observation) != int(expected_peer_count):
        return False
    return 1 <= int(ordinal) <= int(expected_peer_count)


def residual(description: Description, observation: Mapping[str, Any],
             index: int) -> str | None:
    """What the description is STILL missing to name this element alone, or None if it already does.

    THE FIRST GAP, MEASURED 2026-11-16: 318 of 1415 actionable elements have neither own words nor
    an id -- an SVG `circle` with class `init-black`, a bare `rect`. A description built only from
    name-like properties is empty for them, and an empty description is not evidence that the page
    cannot say which one it is: the page says it by CLASS and by ORDER among the class, both of which
    the observation carries. This returns the named gap so a caller can price it, instead of silently
    reporting a 3.32-bit description as if the page were ambiguous.
    """
    found = identify(description, observation)
    if len(found) <= 1:
        return None
    if not description.own and not description.id:
        if description.classes or description.tag:
            return "NAMED_BY_CLASS_AND_ORDER_ONLY__THE_PAGE_SAYS_WHICH_ONE_BY_ITS_POSITION"
        return "NOTHING_IN_THE_OBSERVATION_NAMES_IT__GEOMETRY_IS_ALL_THAT_IS_LEFT"
    return "THE_NAME_REPEATS__ORDER_SEPARATES_THE_TWINS"



def bits(description: Description, observation: Mapping[str, Any], *,
         use: tuple[str, ...] = ("own", "id", "classes", "tag")) -> float:
    """log2 of how many elements this description does NOT separate. 0 means it names one element.

    This is the same unit the recorded one-success run reports as `descriptions_left`, so a learned
    description and a live page can be priced against each other without conversion.
    """
    found = identify(description, observation, use=use)
    return 0.0 if len(found) <= 1 else math.log2(len(found))


def round_trip_problem(description: Description, index: int,
                       observation: Mapping[str, Any], *,
                       use: tuple[str, ...] = ("own", "id", "classes", "tag")) -> str | None:
    """Why a stored description could not re-find the element it was made from, or None.

    THIS IS THE CHECK THE TWO-LANGUAGE DEFECT NEEDED. A skill is only reachable if the description it
    stored still picks out the element that was acted on. It is cheap to run and it fails loudly
    instead of producing a 70% that is secretly a different number.
    """
    found = identify(description, observation, use=use)
    if not found:
        return "REFUTED__THE_DESCRIPTION_NOW_MATCHES_NOTHING"
    if index not in found:
        return "REFUTED__THE_DESCRIPTION_NO_LONGER_MATCHES_THE_ELEMENT_IT_WAS_MADE_FROM"
    if len(found) > 1:
        return f"AMBIGUOUS__{len(found)}_ELEMENTS_ARE_INDISTINGUISHABLE_BY_IT"
    return None
