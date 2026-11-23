"""A goal, a door, and the measurement that joins them.

THE BOTTLENECK THIS ANSWERS
---------------------------
`the_machine_publishes_its_own_doors_v1` discovered 76 doors and its own verdict
named the next wall: *nothing connects a goal to a door*. The census records a
coarse kind (`CREATES`, `RENAMES`, ...); a request arrives as a goal. Nothing
answered "which of these doors does what I was asked".

THE FIRST ATTEMPT, AND WHY IT WAS WRONG
---------------------------------------
The first version of this module ranked doors by a per-CONTENT condition
(ABSENT / PRESENT / SAME / DIFFERENT). Measured on 62 real rows it scored
precision **0.4677** leave-one-out and 0.0 on the held-out tool. The diagnosis
was not tuning: a content-level condition is the wrong unit. Thirty-three gzip
requests produced thirty-three *different* contents, so the predictor had nothing
to transfer -- it sorted candidates by name and called that a choice. A join over
identities cannot generalize across identities; that is a fact about the unit,
not about the ranking.

THE UNIT THAT DOES GENERALIZE: THE PROJECT'S OWN FIVE RELATIONS
--------------------------------------------------------------
`the_vocabulary_is_the_artifact_v1` already states a goal as one of five
relations over an attested state:

    CARD      how many things are there
    MULTISET  which contents, and how many of each
    ORDER     the sequence
    IDENT     the names
    PAIRING   which name holds which content

Those five are the vocabulary the project trusts enough to have measured A1-A5
on. A door's effect is WHICH RELATIONS MOVED, and in which direction -- and that
is a property of the door's *kind*, not of the files it happened to touch. A
rename moves PAIRING with CARD unchanged whether the program is `mv`, `gzip`, or
something nobody has written yet.

So the saved row is a signature:

    (tool, signature over 5 relations, direction, artifact span)

It contains no path, no argv, no content, and no example. That is the answer to
"what should he save": not the experience, the *relation shape* of it. The user's
objection was exact -- exact experiences are never needed again because
environments change -- and a relation shape is the part that does not change.

WHAT IS MEASURED AND WHAT IS REFUSED
------------------------------------
- `signature(before, after)` uses the project's own `relation_value`, imported,
  not reimplemented.
- `choose(goal, records)` matches the relations the goal needs against the
  relations each door was measured to move. No ranking by name, no tie-break by
  alphabetical order: doors that do not move the needed relation are not
  candidates.
- A goal that names something outside the five relations (a semantic property:
  "this file is a PNG", "the text is in French") is UNSTATEABLE and is refused
  with that word, not guessed at.

ZERO PARAMETERS, ZERO MODEL CALLS
---------------------------------
Nothing here is learned by fitting. The "generalization" is that the row's unit
is a relation, so a row measured on one tool is about a class of moves. The
leave-one-out and held-out numbers in the receipt are the test of that claim.
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

# The project's own vocabulary. Imported so that this module cannot quietly
# drift from the five relations the rest of the project measured A1-A5 on.
from canonical.tools.the_vocabulary_is_the_artifact_v1 import relation_value

SCHEMA = "PROJECT_BRAIN_GOAL_TO_DOOR_V1"

RELATIONS = ("CARD", "MULTISET", "ORDER", "IDENT", "PAIRING")

#: The project's five relations are all COMMUTATIVE: they are functions of a SET of
#: (name, content) pairs, so swapping the names of `a` and `b` is indistinguishable
#: from swapping the contents of `a` and `b`. Measured on 20 real doors: all five
#: signatures collapsed into 3 classes, and `rm --force in.txt` was identical to
#: `gzip --force in.txt`. Both delete a name; only one destroys the content.
#:
#: LOT is the relation that separates them, and it is a function of the TRANSITION
#: rather than of one state: a content is LOST when it was readable before and is
#: unreadable after, and RETAINED when it is readable after under any name. It is
#: not a sixth observable -- it is `MULTISET` read across the step, which is why the
#: project's `effect()` could never see it: that function compares two states for
#: equality and throws away which one came first.
LOT = "LOT"
RETAINED = "RETAINED"
LOST = "LOST"
PARTIAL = "PARTIAL"
SAME = "SAME"
CHANGED = "CHANGED"
INCREASED = "INCREASED"
DECREASED = "DECREASED"

NAMES_NOTHING = "NAMES_NOTHING"
NAMES_OUTPUT = "NAMES_OUTPUT"
NAMES_PAIR = "NAMES_PAIR"

_SPAN_WORDS = {
    NAMES_PAIR: ("source", "target", "from", "into", "move", "rename", "copy"),
    NAMES_OUTPUT: ("output", "write", "create", "archive", "file", "remove", "delete",
                   "unlink"),
}


# --------------------------------------------------------------------------- #
# state -> tuple form, so the project's own relation_value can read it
# --------------------------------------------------------------------------- #
def as_state(state: Any) -> list[tuple[str, str]]:
    """`[(name, content)]` from a mapping of files or a machine's own reader.

    The two surfaces the project has disagree about nothing that matters here:
    a `Machine.read()` yields `(ident, content)`, and the census's directory read
    yields `(path, bytes)`. Both become the same tuple list, so one vocabulary
    reads both.
    """
    if isinstance(state, Mapping):
        return [(str(name), _content(value)) for name, value in state.items()]
    return [(str(entry[0]), _content(entry[1])) for entry in state]


def _content(value: Any) -> str:
    """A byte string's identity, without pretending to decode it.

    The first version decoded with `errors="replace"`, and that made two contents
    with no text meaning collide: a gzip stream and any other binary both became
    the same run of U+FFFD. Measured: `rm --force in.txt` and `gzip --force in.txt`
    were reported with the same LOT, so a delete and a compression looked alike.
    Bytes are now identified by their own digest and tagged, so a binary is a
    distinct content from every other binary and from every text.
    """
    if isinstance(value, bytes):
        return "bytes:" + hashlib.sha256(value).hexdigest()
    return "text:" + str(value)


def signature(before: Any, after: Any) -> dict[str, str]:
    """Which of the five relations moved, and which way. This is the saved row.

    The whole point of the unit: `mv`, `gzip -k`, and `cp` followed by `rm` all
    produce the same signature (CARD SAME, PAIRING CHANGED) because they are the
    same MOVE of the state, however differently they are spelled. A signature is
    a statement about the class of the move, which is what a new environment can
    use; the filenames it was measured on are not carried and never could be used
    again.
    """
    b, a = as_state(before), as_state(after)
    out: dict[str, str] = {}
    for relation in RELATIONS:
        was, now = relation_value(relation, b), relation_value(relation, a)
        if was == now:
            out[relation] = SAME
        elif relation == "CARD":
            out[relation] = INCREASED if now > was else DECREASED
        else:
            out[relation] = CHANGED
    # LOT is computed from the RAW states, not from the normalised tuples: the
    # tuples have already turned every binary into a digest string, so a compressed
    # file can no longer be opened to see what it holds. Measured: passing (b, a)
    # made a compression report LOST, which is the exact confusion between "the
    # name is gone" and "the bytes are gone" that this relation exists to prevent.
    out[LOT] = lot(before, after)
    return out


def _contents(state: Sequence[tuple[str, str]]) -> set[str]:
    return {content for _name, content in state}


def _payload_digest(blob: bytes) -> str:
    """One identity for "the content a reader could recover from these bytes"."""
    try:
        import gzip as _gzip
        return hashlib.sha256(_gzip.decompress(blob)).hexdigest()
    except Exception:
        return hashlib.sha256(blob).hexdigest()


def lot(before: Any, after: Any) -> str:
    """RETAINED, LOST, or PARTIAL: can every content still be recovered?

    This is the one relation the project's vocabulary could not express, because
    the other five are properties of a state and this is a property of the step.
    `mv a b` retains every content. `rm a` loses one. `gzip a` retains it, one
    layer down, inside `a.gz`. Nothing here is a tool name: three programs, one
    question, and the third is the one that needed the bytes to be read as content
    rather than as a filename.
    """
    was = {_payload_digest(blob) for blob in _blobs(before)}
    now = {_payload_digest(blob) for blob in _blobs(after)}
    if not was:
        return RETAINED
    kept = was & now
    if kept == was:
        return RETAINED
    return LOST if kept == set() else PARTIAL


def _blobs(state: Any) -> list[bytes]:
    if isinstance(state, Mapping):
        return [value if isinstance(value, bytes) else str(value).encode()
                for value in state.values()]
    return [entry[1] if isinstance(entry[1], bytes) else str(entry[1]).encode()
            for entry in state]


def moved(signature_of_pair: Mapping[str, str]) -> dict[str, str]:
    """Only what moved. A signature is mostly SAME, and SAME is the noise.

    LOT is different from the other five: RETAINED is its "nothing happened to the
    content" value and is dropped like SAME, while LOST and PARTIAL are kept. That
    is deliberate -- a goal is a demanded CHANGE, and "the content survived" is not
    a change a door can be asked to make.
    """
    out = {}
    for rel, value in signature_of_pair.items():
        if rel == LOT:
            if value == RETAINED:
                continue
        elif value == SAME:
            continue
        out[rel] = value
    return out


# --------------------------------------------------------------------------- #
# the goal: which relation must move, and which way
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Goal:
    """A request, stated as a demanded change in the vocabulary's five relations.

    `need` maps a relation to the direction it must move. `content` and `name`
    are carried for the RECORD (so a receipt says which content was asked about)
    but are deliberately not used to choose a door: choosing by identity is the
    defect this design replaced.
    """
    need: tuple[tuple[str, str], ...]
    content: str = ""
    name: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"need": dict(self.need), "content": self.content, "name": self.name}


#: The five relations and the one added here, as names a caller can refer to
#: without writing a string literal: `G.CARD` cannot be misspelled into a goal
#: that silently matches nothing.
CARD, MULTISET, ORDER, IDENT_V, PAIRING = RELATIONS
IDENT = IDENT_V

#: Every relation a goal may be stated over: the project's five, plus the one
#: relation this module adds because the five are commutative and cannot tell a
#: rename from a delete.
VOCABULARY = RELATIONS + (LOT,)

#: The values each relation may take. A goal that asks for a value outside these
#: is malformed, and saying so is cheaper than ranking doors against nonsense.
VALUES = {"CARD": (SAME, INCREASED, DECREASED, CHANGED),
          "MULTISET": (SAME, CHANGED), "ORDER": (SAME, CHANGED),
          "IDENT": (SAME, CHANGED), "PAIRING": (SAME, CHANGED),
          LOT: (RETAINED, LOST, PARTIAL)}


def stateable(goal: Goal) -> bool:
    """Can the vocabulary express this goal at all?

    The defect this replaces: the check was written against `RELATIONS`, which does
    not include LOT, so every goal that mentioned retention was called UNSTATEABLE
    and refused. Measured cost: `rm` answered 0 of 21 held-out requests while `cp`
    and `mv` answered all of theirs -- a bug that looked exactly like a finding.
    """
    if not goal.need:
        return False
    for relation, direction in goal.need:
        if relation not in VOCABULARY:
            return False
        if direction not in VALUES[relation]:
            return False
    return True


def satisfied(goal: Goal, before: Any, after: Any) -> bool:
    """Did this exact transition do what was asked? Measured against the relations."""
    got = signature(before, after)
    return all(got.get(rel) == direction for rel, direction in goal.need)


def goal_for(before: Any, after: Any, content: str = "", name: str = "") -> Goal:
    """The goal a real transition satisfied, stated in the vocabulary.

    This is how a measured run becomes a request: whatever moved, that is what the
    door did, and that is the goal another door can be asked about.
    """
    return Goal(need=tuple(sorted(moved(signature(before, after)).items())),
                content=content, name=name)


# --------------------------------------------------------------------------- #
# the door: a signature and a span, never an example
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Record:
    """One door, as the class of move it makes. No path, no argv, no content."""
    door_id: str
    tool: str
    signature: tuple[tuple[str, str], ...]
    artifact_span: str = NAMES_OUTPUT

    @property
    def spans_an_artifact(self) -> bool:
        return self.artifact_span != NAMES_NOTHING

    def moves(self) -> dict[str, str]:
        return dict(self.signature)


def record_of(door: Mapping[str, Any], before: Any, after: Any) -> Record:
    return Record(door_id=str(door.get("door") or door.get("id") or ""),
                  tool=str(door.get("tool") or ""),
                  signature=tuple(sorted(moved(signature(before, after)).items())),
                  artifact_span=door.get("artifact_span") or NAMES_OUTPUT)


def artifact_span(declared: str | None, flag: str = "", description: str = "") -> str:
    """What the program's own declaration says the door writes.

    Read from the declaration, never from a table of tool names. `NAMES_NOTHING`
    is the answer for a program whose words name no artifact at all -- which is
    the same fact that makes it a sensor rather than a door.
    """
    words = " ".join([declared or "", flag or "", description or ""]).lower()
    if any(word in words for word in _SPAN_WORDS[NAMES_PAIR]) and \
            sum(1 for word in _SPAN_WORDS[NAMES_PAIR] if word in words) >= 2:
        return NAMES_PAIR
    if any(word in words for word in _SPAN_WORDS[NAMES_OUTPUT]):
        return NAMES_OUTPUT
    return NAMES_NOTHING


# --------------------------------------------------------------------------- #
# the join
# --------------------------------------------------------------------------- #
def speaks_to(record: Record, goal: Goal) -> bool:
    """A door is a candidate only if it moves every relation the goal demands.

    No scoring, no ordering by how close it came. A door measured to increase
    CARD is not a weaker candidate for a goal that needs CARD unchanged; it is
    the wrong move, and offering it would be the guessing this project exists to
    remove.
    """
    if not record.spans_an_artifact:
        return False
    have = record.moves()
    return all(have.get(rel) == direction for rel, direction in goal.need)


def choose(goal: Goal, records: Sequence[Record]) -> dict[str, Any]:
    """The doors that make this exact move, or a refusal that says why."""
    if not stateable(goal):
        return {"schema": SCHEMA, "goal": goal.as_dict(), "verdict": "UNSTATEABLE",
                "reason": ("this goal is not stated over the five relations, so no "
                           "measured door can be matched to it"),
                "candidates": []}
    if not goal.need:
        return {"schema": SCHEMA, "goal": goal.as_dict(), "verdict": "NO_DOOR",
                "reason": "this goal demands no change, so no door is needed",
                "candidates": []}
    hits = [record for record in records if speaks_to(record, goal)]
    if not hits:
        return {"schema": SCHEMA, "goal": goal.as_dict(), "verdict": "NO_DOOR",
                "reason": ("no measured door makes this move; the nearest doors are "
                           "reported with the move they actually make"),
                "candidates": []}
    return {"schema": SCHEMA, "goal": goal.as_dict(), "verdict": "MATCHED",
            "door": hits[0].door_id, "tool": hits[0].tool,
            "candidates": [hit.door_id for hit in hits],
            "matches": len(hits),
            "selectivity": selectivity(goal, records),
            "reason": "this door was measured to make exactly this move"}


def selectivity(goal: Goal, records: Sequence[Record]) -> dict[str, Any]:
    """How much the match NARROWS the doors -- the number a match alone hides.

    Measured on real rows: the move `mv` makes was matched by 59 doors while the
    move `rm` makes was matched by 3. Both are "MATCHED", and reporting only that
    would let a join that never discriminates look perfect. A move matched by every
    door carries no information: it says the vocabulary cannot separate the doors,
    which is a fact about the vocabulary worth reporting, not a success.
    """
    total = [record for record in records if record.spans_an_artifact]
    hits = [record for record in total if speaks_to(record, goal)]
    share = round(len(hits) / len(total), 4) if total else None
    if not hits:
        verdict = "NO_MATCH"
    elif len(hits) == len(total):
        verdict = "UNINFORMATIVE__EVERY_DOOR_MATCHES"
    elif share is not None and share >= 0.5:
        verdict = "WEAK__MORE_THAN_HALF_MATCH"
    else:
        verdict = "DISCRIMINATING"
    return {"candidates_considered": len(total), "matched": len(hits),
            "fraction_matched": share, "verdict": verdict}


# --------------------------------------------------------------------------- #
# the two honest measures of generalization
# --------------------------------------------------------------------------- #
def held_out(rows: Sequence[Mapping[str, Any]], tool: str) -> dict[str, Any]:
    """Can this tool's requests be answered from OTHER tools' measurements?

    This is the generalization claim, stated so that it can fail. Every row for
    `tool` is a move that tool really made. The predictor sees no row of `tool`,
    and for each such request is asked: do the other tools contain a door that
    makes the same move? It is right when it names one, and right to refuse when
    none exists -- a refusal is a stated limit, not a pass and not a miss.

    The interesting case is when the answer is YES from an unrelated program: a
    move measured on `gzip` (which renames a file into a compressed twin) is the
    same move `mv` makes, and if the signature is the right unit, the join finds
    it without ever having run `mv`.
    """
    kept = [r for r in rows if r["tool"] != tool]
    asked = [r for r in rows if r["tool"] == tool]
    records = [record_of(r, r["before"], r["after"]) for r in kept]
    found = refused = 0
    details = []
    for row in asked:
        goal = goal_for(row["before"], row["after"], name=str(row.get("goal", "")))
        goal = Goal(need=goal.need)
        choice = choose(goal, records)
        hit = choice["verdict"] == "MATCHED"
        found += hit
        refused += not hit
        details.append({"request": dict(goal.need), "verdict": choice["verdict"],
                        "tool_named": choice.get("tool")})
    # coverage is the control a bare answer rate needs: if every door matched every
    # request the answer rate would be 1.0 and mean nothing.
    matches = [len([r for r in records if speaks_to(r, Goal(need=tuple(sorted(
        moved(signature(row["before"], row["after"])).items()))))])
        for row in asked]
    considered = len([r for r in records if r.spans_an_artifact])
    return {"held_out_tool": tool, "requests": len(asked),
            "answered_from_other_tools": found, "refused": refused,
            "answer_rate": round(found / len(asked), 4) if asked else None,
            "mean_matches_per_request": round(sum(matches) / len(matches), 2) if matches else None,
            "candidates_considered": considered,
            "evidence_rows": len(kept), "details": details}


def transfer(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Leave-one-out: for each real request, is the move found among the others?

    The question is deliberately about the MOVE, not about the door's identity.
    A row never votes on itself, so a door cannot make its own request look
    answerable.
    """
    rows = list(rows)
    right = wrong = 0
    per_move: dict[str, dict[str, int]] = {}
    for row in rows:
        others = [r for r in rows if r is not row]
        goal = Goal(need=goal_for(row["before"], row["after"]).need)
        choice = choose(goal, [record_of(r, r["before"], r["after"]) for r in others])
        key = json.dumps(dict(goal.need), sort_keys=True)
        bucket = per_move.setdefault(key, {"asked": 0, "answered": 0, "refused": 0})
        bucket["asked"] += 1
        if choice["verdict"] == "MATCHED":
            right += 1
            bucket["answered"] += 1
        else:
            wrong += 1
            bucket["refused"] += 1
    asked = len(rows)
    return {"schema": SCHEMA, "attempts": asked, "answered": right, "refused": wrong,
            "answer_rate": round(right / asked, 4) if asked else None,
            "per_move": sorted(({"move": key, **value} for key, value in per_move.items()),
                               key=lambda b: (-b["asked"], b["move"])),
            "authority": "NONE__PRODUCER_RUN_SANDBOX",
            "note": ("a refusal means no OTHER door made that move; it is the honest "
                     "limit of predicting a move from a single run, not an error")}


def unstateable_report() -> dict[str, Any]:
    """What the five relations cannot express, stated as the one thing they lack.

    The vocabulary reads structure: how many, which names, which contents, in what
    order, paired how. It cannot read MEANING -- whether a file is a valid PNG,
    whether a sentence is in French, whether an archive is intact. Those are goals
    outside the vocabulary, and this module refuses them by name rather than
    ranking doors by a guess.
    """
    return {
        "expressible": list(VOCABULARY),
        "not_expressible": ["MEANING", "VALIDITY", "LANGUAGE", "SEMANTIC_TYPE"],
        "why": ("the five relations are functions of the attested structure; a goal "
                "about what the bytes MEAN is not a function of that structure, so no "
                "door can be matched to it by this join"),
        "refused_by": "choose() returns UNSTATEABLE",
    }
