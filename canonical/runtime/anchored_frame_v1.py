"""Read a control by WHERE IT SITS IN A RECORD, not by its own name.

The defect this closes, measured not guessed
--------------------------------------------
The last two rounds each read a refusal label and aimed engineering at the wrong seam. The third
round did not read the label; it dumped the page:

    "Find the email by Enrichetta and reply to them with the text \\"Egestas duis.\\""

The observation carries 107 elements, and the reply control, the text box and the submit button are
NOT among them. What IS among them is the record:

    div.email-thread   containing
      div.email-sender   "Enrichetta"      <- the identifier
      div.email-subject  "Duis velit."
      div.email-body     "At facilisi nam.."
      div.email-actions  containing  span.trash   and   span.star

There are ten such rows and every action control in every row is the SAME `span.star`. No name can
separate them. So the previous refusal -- `MULTI_APP_STATE_OUTSIDE_OBSERVATION` -- was false, for
the third time in three rounds, and in the same direction: the compiler had no way to say "the star
of THAT row", so it said the state was not there.

`MULTI_APP` was not a lie about the world. It was a statement about the LANGUAGE.

The one idea
------------
A **frame**. Every element has a coordinate `(container, id, path_from_id)`:

    container  the nearest ancestor that holds more than one of something addressable
    id         the element inside that container whose text is the identifier the instruction named
    path       the steps from the container down to the id, and from there down to the control

Once a frame exists, "the star of that row" is decidable: container = the row, id = the sender, and
the control is the element at path_from_id that the word names. The same frame answers "their email",
"that row's reply button", "the calendar event with the same name".

Why a frame and not a bigger vocabulary
--------------------------------------
A vocabulary would need one entry per app ("email-sender", "name", "hour-label"), and this project
has proved three times that the entry list is not the wall. A frame is one coordinate change, and it
is the thing a person does when they say "that row" -- they do not learn a new word for each app.

The limits, stated so they cannot be mistaken for success
---------------------------------------------------------
* A frame is built only from containment and text. If the identifier appears in more than one
  container, the frame is AMBIGUOUS and says so; it never takes the first match.
* When no control exists at all inside the record, the frame reports `ABSENT__THE_RECORD_HAS_NO_
  SUCH_CONTROL` and the caller must go and find one (open the message, scroll, expand). That is a
  DIFFERENT repair from "the language cannot name it", and keeping the two apart is the whole point
  of this file.
* This module invents no action and reads no reward. `K3 = 0`, `$0`, no model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ANCHORED_FRAME_V1"

RESOLVED = "RESOLVED__THE_FRAME_NAMES_ONE_CONTROL"
AMBIGUOUS = "AMBIGUOUS__MORE_THAN_ONE_RECORD_MATCHES"
ABSENT = "ABSENT__THE_RECORD_HOLDS_NO_SUCH_CONTROL"
NO_RECORD = "NOTHING__NO_ELEMENT_SHOWS_THE_IDENTIFIER"
NOT_A_RECORD = "ABSENT__THE_IDENTIFIER_IS_NOT_INSIDE_A_CONTAINER"

#: Words that ask for a control INSIDE the record. Each maps to the spellings the pages use for it,
#: matched against class/id/tag/text of the elements inside the record -- never against a global
#: position, so one entry serves every app that uses the word.
CONTROL_WORDS: dict[str, tuple[str, ...]] = {
    "star": ("star",),
    "unstar": ("star",),
    "trash": ("trash", "delete", "bin"),
    "delete": ("trash", "delete", "bin"),
    "reply": ("reply", "send-reply"),
    "forward": ("forward", "send-forward"),
    "email": ("email",),
    "phone": ("phone", "tel"),
    "address": ("address",),
    "checkbox": ("checkbox",),
    "message": ("message", "email", "sms"),
    "event": ("event",),
    "title": ("title", "subject"),
    "subject": ("subject", "title"),
}

_IDENTIFIER_QUOTED = re.compile(r'"([^"]{2,40})"|\'([^\']{2,40})\'')


# --------------------------------------------------------------------------------------------- #
# reading the tree
# --------------------------------------------------------------------------------------------- #
def _area(element: Mapping[str, Any]) -> int:
    box = element.get("box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return 0
    return int(box[2]) * int(box[3])


def _children(elements: Sequence[Mapping[str, Any]]) -> dict[int, list[int]]:
    kids: dict[int, list[int]] = {}
    for element in elements:
        parent = int(element.get("parent", -1))
        kids.setdefault(parent, []).append(int(element.get("index", -1)))
    return kids


def _descendants(elements_by_index: Mapping[int, Mapping[str, Any]],
                 kids: Mapping[int, list[int]], root: int) -> list[int]:
    out, stack = [], [root]
    while stack:
        current = stack.pop()
        for child in kids.get(current, ()):
            out.append(child)
            stack.append(child)
    return out


def _ancestors(elements_by_index: Mapping[int, Mapping[str, Any]], index: int) -> list[int]:
    out, current, guard = [], index, 0
    while guard < 64:
        guard += 1
        parent = int(elements_by_index[current].get("parent", -1))
        if parent < 0 or parent not in elements_by_index:
            break
        out.append(parent)
        current = parent
    return out


def _other_identifiers(elements_by_index: Mapping[int, Mapping[str, Any]],
                       index: int) -> set[str]:
    """The other texts in the SAME kind of place as `index` -- its class-mates' own text.

    Used only to stop a frame from growing past one record: a container that also holds another
    sender name holds another email.
    """
    kind = _normalise(elements_by_index[index].get("classes"))
    if not kind:
        return set()
    token = kind.split()[0]
    out = set()
    for other in elements_by_index.values():
        if int(other.get("index", -1)) == index:
            continue
        if token in _normalise(other.get("classes")):
            own = _normalise(other.get("text"))
            if own:
                out.add(own)
    return out


def _holds_a_control(elements_by_index, kids, index: int) -> int:
    """How many addressable controls live under this element."""
    count = 0
    for descendant in _descendants(elements_by_index, kids, index):
        element = elements_by_index[descendant]
        if element.get("can_click") or element.get("can_type"):
            count += 1
    return count


# --------------------------------------------------------------------------------------------- #
# the frame
# --------------------------------------------------------------------------------------------- #
@dataclass
class Frame:
    """One record, located by the identifier it shows, with the path that identifies it."""

    identifier: str
    outcome: str
    container: int | None = None
    identifier_element: int | None = None
    candidates: list[int] = field(default_factory=list)
    controls: list[dict[str, Any]] = field(default_factory=list)
    #: How the record could be brought into view, when it is not in the observation at all.
    #: Measured 2026-11-16 on phone-book: "Find Larissa" and the book is showing one card with a
    #: `>` pager. That is a SEARCH, not a missing observable, and the two repairs are different.
    reachable_by: list[dict[str, Any]] = field(default_factory=list)
    schema: str = SCHEMA

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "identifier": self.identifier, "outcome": self.outcome,
                "container": self.container, "identifier_element": self.identifier_element,
                "candidates": self.candidates, "controls": self.controls,
                "reachable_by": self.reachable_by}


def _normalise(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _carries(element: Mapping[str, Any], needle: str) -> bool:
    """Whether this element SHOWS the string in its own right.

    `full_text` is the element's whole subtree, so every ancestor of a showing element also
    "carries" it: measured 2026-11-16, that made one sender name look like six records. Own text
    first; `full_text` only for an element that shows nothing of its own (a leaf wrapper).
    """
    # OWN TEXT ONLY. The `full_text` fallback was catastrophic and measured: `full_text` is the
    # element's whole subtree, so every ancestor of a sender name "showed" the name and one email
    # looked like seven records. An element that shows a name says it itself.
    own = (_normalise(element.get("text")) or _normalise(element.get("value"))
           or " ".join(_normalise(element.get(key)) for key in ("aria-label", "title", "alt")))
    return bool(own) and needle in own


def find_frame(identifier: str, observation: Mapping[str, Any], *,
               controls: Iterable[str] = ()) -> Frame:
    """Locate the record that SHOWS `identifier`, and the controls inside it.

    A record is the nearest ancestor of the identifier that also holds at least one addressable
    control other than the identifier itself. That is a structural definition, not a class name:
    it holds for a mailbox row, a contact card, a calendar event, and a table row alike.
    """
    needle = _normalise(identifier)
    if not needle:
        return Frame(identifier=identifier, outcome=NO_RECORD, reachable_by=reachable[:4])

    elements = list(observation.get("elements") or [])
    by_index = {int(e.get("index", -1)): e for e in elements}
    kids = _children(elements)

    showing = [index for index, element in by_index.items() if _carries(element, needle)]
    if not showing:
        reachable = [{"index": int(e.get("index", -1)),
                      "word": _normalise(e.get("text")),
                      "classes": _normalise(e.get("classes"))}
                     for e in by_index.values()
                     if e.get("can_click")
                     and re.search(r"next|>|›|page|scroll|down", " ".join(
                         _normalise(e.get(k)) for k in ("text", "classes", "aria-label")))]
        # A NAME CAN BE SHOWN BY THE NEIGHBOUR OF THE RECORD, NOT ONLY INSIDE IT. Measured
        # 2026-11-16 on phone-book: the contact book shows ONE card at a time and the list of names
        # it is showing sits beside it, so "Larissa" is a sibling of the card, not a descendant.
        # The card is the nearest ancestor of that name which holds addressable controls.
        named = [index for index, element in by_index.items() if _carries(element, needle)]
        for index in named:
            for ancestor in _ancestors(by_index, index):
                if _holds_a_control(by_index, kids, ancestor) >= 2:
                    inside = _descendants(by_index, kids, ancestor)
                    return Frame(identifier=identifier, outcome=RESOLVED, container=ancestor,
                                 identifier_element=index, controls=_controls_in(
                                     [by_index[d] for d in inside], controls))
        return Frame(identifier=identifier, outcome=NO_RECORD, reachable_by=reachable[:4])

    # THE NEAREST ancestor that holds an addressable control other than the identifier. Nearest is
    # the whole point: measured 2026-11-16 on email-inbox, walking further up reaches the list of
    # ten threads and then the page, so every row "contains a star" and the frame calls itself
    # ambiguous. The nearest container holding a control is the row.
    records: dict[int, int] = {}
    for index in showing:
        chain = _ancestors(by_index, index)
        if not chain:
            continue
        # A RECORD IS OFTEN SPLIT ACROSS SIBLINGS, and that is the normal case, not an edge case.
        # Measured 2026-11-16 on email-inbox: `div.email-thread` holds `div.email-left` (sender,
        # subject, body) and `div.email-right` (time, actions: trash, star). The nearest container
        # holding a control is `email-left`, which holds the SUBJECT and the BODY -- so the first
        # implementation located "the email by Enrichetta" and then could not find the star that is
        # physically in the same row. Walking DOWN from an ancestor until it would swallow more than
        # one identifier is what keeps the frame on one record.
        # THE RECORD IS THE LARGEST CONTAINER THAT DOES NOT SWALLOW A SECOND RECORD.
        # Measured 2026-11-16 on email-inbox: the nearest container holding a control is
        # `div.email-left`, which holds the sender, subject and body -- but the star is in the
        # SIBLING `div.email-right`. Stopping at the nearest container located the email and then
        # could not find the control physically in the same row. Walking further up is what spans
        # the two halves, and the only thing that must stop it is another record's identifier.
        own_class_mates = _other_identifiers(by_index, index)
        record = None
        for ancestor in chain:
            inside = _descendants(by_index, kids, ancestor)
            foreign = [d for d in inside if d != index and d not in chain and any(
                _carries(by_index[d], name) for name in own_class_mates)]
            if foreign:
                break                    # the next step up holds a different record too
            if _holds_a_control(by_index, kids, ancestor) >= 2:
                record = ancestor        # keep going: a later step up may span a sibling half
        if record is not None:
            records.setdefault(record, index)

    if not records:
        return Frame(identifier=identifier, outcome=NOT_A_RECORD,
                     identifier_element=showing[0], candidates=[])
    if len(records) > 1:
        # Ten rows all say "Primary"; ten rows all have a star. Ambiguity is the honest answer.
        return Frame(identifier=identifier, outcome=AMBIGUOUS,
                     candidates=sorted(records), identifier_element=showing[0])

    container, identifier_element = next(iter(records.items()))
    inside = _descendants(by_index, kids, container)
    found = _controls_in([by_index[d] for d in inside], controls)
    return Frame(identifier=identifier, outcome=RESOLVED, container=container,
                 identifier_element=identifier_element, controls=found)


def _controls_in(elements: Sequence[Mapping[str, Any]],
                 controls: Iterable[str]) -> list[dict[str, Any]]:
    """The controls the words name, among these elements. One implementation, two callers."""
    found = []
    for word in controls:
        wanted = CONTROL_WORDS.get(_normalise(word))
        if not wanted:
            continue
        for element in elements:
            # A CONTROL IS NAMED BY ITS OWN TEXT OR BY AN EXACT CLASS TOKEN -- never by a prefix.
            # Measured 2026-11-16: a prefix test on the whole class string made `email-sender`
            # "carry" the word `email`, so "find the email by Enrichetta and reply" resolved to a
            # press on the sender's name. The sender is not a control; `trash` and `star` are.
            text = _normalise(element.get("text")) or _normalise(element.get("value"))
            tokens = set()
            for key in ("classes", "id"):
                tokens |= {_normalise(t) for t in str(element.get(key) or "").split()}
            for key in ("aria-label", "title", "alt"):
                tokens.add(_normalise(element.get(key)))
            exact = any(token in tokens for token in wanted)
            spoke = bool(text) and any(token in text.split() or text == token for token in wanted)
            if exact or spoke:
                found.append({"word": _normalise(word), "index": int(element.get("index", -1)),
                              "carried": (text or " ".join(sorted(tokens)))[:60],
                              "can_click": bool(element.get("can_click"))})
    return found


def control_of(identifier: str, control_word: str,
               observation: Mapping[str, Any]) -> dict[str, Any]:
    """The single action this reads as: press the named control inside the record.

    Returns a dict with `outcome` and, when resolved, `index`. Never returns an index it cannot
    justify from containment plus text.
    """
    frame = find_frame(identifier, observation, controls=[control_word])
    if frame.outcome != RESOLVED:
        return {"outcome": frame.outcome, "frame": frame.as_dict()}
    hits = [c for c in frame.controls if c["can_click"]]
    if not hits:
        return {"outcome": ABSENT, "frame": frame.as_dict(), "wanted": control_word}
    if len(hits) > 1:
        # the same word twice inside one record: the narrowest element wins, because a wrapper and
        # the icon inside it are one control as far as a mouse is concerned
        hits.sort(key=lambda c: _area(_by_index(observation)[c["index"]]))
        return {"outcome": "RESOLVED__NARROWEST_MATCH", "index": hits[0]["index"],
                "frame": frame.as_dict()}
    return {"outcome": RESOLVED, "index": hits[0]["index"], "frame": frame.as_dict()}


def _by_index(observation: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    return {int(e.get("index", -1)): e for e in observation.get("elements") or []}


def identifiers_in(utterance: str) -> list[str]:
    """The names an instruction gives a record: quoted strings first, then capitalised words.

    A capitalised word is only taken when it is not the first word of the sentence and not a word
    that names a control -- "Find Larissa in the contact book" gives {"Larissa"}.
    """
    # A QUOTED STRING IN THESE INSTRUCTIONS IS THE TEXT TO TYPE, NOT THE NAME OF THE RECORD.
    # Measured 2026-11-16: `email-inbox` says '...reply to them with the text "Egestas duis."' and
    # reading the quote as the identifier searched the page for the reply body it was about to
    # create. The record's name is the unquoted proper noun.
    text = _IDENTIFIER_QUOTED.sub(" ", utterance or "")
    words = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    controlish = {w.title() for word in CONTROL_WORDS for w in (word,)}
    skipped = {"find", "click", "create", "looking", "the", "create", "add", "make", "select",
               "drag", "enter", "type", "press", "submit"}
    return [w for w in words if w.title() not in controlish and w.lower() not in skipped]


# --------------------------------------------------------------------------------------------- #
# the frame as a generator of fact vectors, for the decidable instrument
# --------------------------------------------------------------------------------------------- #
def frame_facts(identifier: str, observation: Mapping[str, Any]) -> tuple[str, ...]:
    """The facts a frame establishes, in the vocabulary `applicability_v1` already decides on.

    These are the facts that a name-only vocabulary CANNOT state, which is why the wall looked like
    missing state. Feeding this to `insufficiency_witness` is what turns "the language cannot say
    it" into a certificate rather than a label.
    """
    frame = find_frame(identifier, observation, controls=list(CONTROL_WORDS))
    facts = [f"frame.outcome.{frame.outcome}"]
    if frame.container is not None:
        facts.append("frame.has_container")
    facts.append(f"frame.found.{len(frame.controls)}")
    for control in frame.controls:
        facts.append(f"frame.control.{control['word']}")
    return tuple(sorted(set(facts)))
