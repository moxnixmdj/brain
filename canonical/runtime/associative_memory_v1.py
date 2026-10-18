#!/usr/bin/env python3
"""Memory that decides for itself what is worth keeping.

Not a log, and not a lookup table.

  - flywheel.recall answers "what did I learn about THIS exact key" -- it can
    only return what you already have the key for.
  - h100_zero_learned_event_memory is a hash-chained append-only log -- every
    event is kept forever with equal standing, which is the opposite of memory.
    A creature that remembers everything equally remembers nothing usefully.

Memory, in the sense the owner means, has to do three things a log cannot:

  1. ASSOCIATIVE RETRIEVAL. A partial cue brings back related things. You do
     not need the key; you need to be reminded.
  2. IMPORTANCE IS EARNED, NOT DECLARED. Nothing assigns importance up front.
     An entry becomes important by being retrieved and then HELPING. Importance
     is a consequence, learned from outcomes, which is what makes this a
     creature's memory rather than a ranked list somebody configured.
  3. FORGETTING IS EMERGENT. Importance decays with disuse and the least
     important go first under pressure. Forgetting is not a bug in memory; a
     memory that cannot forget is a log.

Nothing here is tuned per task. There is no list of what matters. The only
signal is: did retrieving this actually help?
"""

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_ASSOCIATIVE_MEMORY_V1"

DEFAULT_STATE = str(
    Path(__file__).resolve().parents[2]
    / "canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json"
)

# Half-life, in days, of an entry that is not being used. Disuse is evidence
# that it was not important, not proof -- so this decays, it does not delete.
HALF_LIFE_DAYS = 7.0
DEFAULT_CAPACITY = 5000

_WORD = re.compile(r"[a-z0-9][a-z0-9_+-]*")

# Function words carry no subject matter. Without this filter, "how to bake
# sourdough bread" recalls "zint encodes barcodes to png" because both contain
# "to" -- shared filler producing 0.17 relevance between two unrelated things.
# A memory that matches on grammar rather than content recalls everything and
# therefore reminds you of nothing. Content words only.
_STOP = frozenset("""
a an and are as at be been being but by can could did do does doing for from
had has have having how i if in into is it its me my no not of on or our shall
should so such than that the their them then there these they this those to
was we were what when where which who whom will with would you your
""".split())


# Inflectional endings. "decoding" and "decode" must land on the same term or
# the memory cannot associate a procedure about decoding with a problem that
# mentions decoding -- which is exactly the reminder it exists to make.
_SUFFIXES = ("ation", "tion", "ion", "ing", "ed", "er", "est", "ly", "ies", "es", "s")


def _variants(word: str) -> set[str]:
    """Word plus its plausible stems, so inflections meet in the middle."""
    out = {word}
    for suf in _SUFFIXES:
        if len(word) <= len(suf) + 2 or not word.endswith(suf):
            continue
        stem = word[: -len(suf)]
        out.add(stem)                      # decoding -> decod
        out.add(stem + "e")                # decod     -> decode
        if len(stem) > 2 and stem[-1] == stem[-2]:
            out.add(stem[:-1])             # running   -> run
        break
    return {v for v in out if len(v) >= 2 and v not in _STOP}


def _terms(text: Any) -> set[str]:
    """Content tokens with their stems, so inflections still recall each other."""
    out: set[str] = set()
    for w in _WORD.findall(str(text or "").lower()):
        if len(w) < 2 or w in _STOP:
            continue
        out |= _variants(w)
    return out


def _now() -> float:
    return time.time()


def _load(path: str = DEFAULT_STATE) -> dict:
    p = Path(path)
    if not p.exists():
        return {"schema": SCHEMA, "entries": {}, "next_id": 1}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("schema") == SCHEMA:
            data.setdefault("entries", {})
            data.setdefault("next_id", 1)
            return data
    except (OSError, ValueError):
        pass
    return {"schema": SCHEMA, "entries": {}, "next_id": 1}


def _save(state: dict, path: str = DEFAULT_STATE) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def remember(content: Any, *, kind: str = "", tags: Iterable[str] = (),
             path: str = DEFAULT_STATE) -> str:
    """Store something. Returns its id. Nothing is asserted about its worth."""
    state = _load(path)
    eid = "m" + str(state["next_id"])
    state["next_id"] += 1
    now = _now()
    state["entries"][eid] = {
        "id": eid,
        "content": content if isinstance(content, (str, int, float, bool)) or content is None
                   else json.dumps(content, sort_keys=True, default=str),
        "kind": str(kind or ""),
        "tags": sorted({str(t).lower() for t in tags}),
        "terms": sorted(_terms(content) | _terms(" ".join(tags)) | _terms(kind)),
        "created": now,
        "last_accessed": now,
        "accesses": 0,
        "credited": 0,   # retrieved and it helped
        "blamed": 0,     # retrieved and it misled
    }
    _save(state, path)
    return eid


def _relevance(cue_terms: set[str], entry: Mapping[str, Any],
               cue_tags: set[str]) -> float:
    """How related, independent of how important. Dice over term sets."""
    eterms = set(entry.get("terms") or ())
    if not cue_terms or not eterms:
        return 0.0
    overlap = len(cue_terms & eterms)
    if not overlap:
        # a cue can still hit a tag even when no word overlaps
        if cue_tags and (cue_tags & set(entry.get("tags") or ())):
            return 0.15
        return 0.0
    dice = (2.0 * overlap) / (len(cue_terms) + len(eterms))
    if cue_tags and (cue_tags & set(entry.get("tags") or ())):
        dice = min(1.0, dice + 0.10)
    return dice


def importance(entry: Mapping[str, Any], *, now: float | None = None) -> float:
    """What this entry has EARNED. Nobody declares it.

    Helping is the only thing that raises it; misleading lowers it; disuse
    decays it. An entry retrieved a hundred times that never helped is worth
    less than one that helped twice -- repeated retrieval without credit is
    evidence it is merely familiar, not useful.
    """
    now = _now() if now is None else now
    credited = float(entry.get("credited") or 0)
    blamed = float(entry.get("blamed") or 0)
    accesses = float(entry.get("accesses") or 0)

    earned = 1.0 + credited
    if blamed:
        earned /= (1.0 + blamed)
    # familiarity without credit is discounted, mildly
    unhelpful = max(0.0, accesses - credited - blamed)
    if unhelpful > 0:
        earned /= (1.0 + 0.05 * unhelpful)

    age_days = max(0.0, (now - float(entry.get("last_accessed") or now)) / 86400.0)
    decay = 0.5 ** (age_days / HALF_LIFE_DAYS)
    return earned * decay


def recall(cue: Any, *, k: int = 5, tags: Iterable[str] = (),
           path: str = DEFAULT_STATE) -> list[dict[str, Any]]:
    """Bring back what matters AND is relevant.

    Ranked by relevance x importance, so a highly relevant entry that never
    helped loses to a moderately relevant one that repeatedly did. That product
    is the whole point: relevance alone is a search engine, importance alone is
    a leaderboard.
    """
    state = _load(path)
    cue_terms = _terms(cue)
    cue_tags = {str(t).lower() for t in tags}
    if not cue_terms and not cue_tags:
        return []

    scored = []
    now = _now()
    for entry in state["entries"].values():
        rel = _relevance(cue_terms, entry, cue_tags)
        if rel <= 0.0:
            continue
        imp = importance(entry, now=now)
        scored.append((rel * imp, rel, imp, entry))

    scored.sort(key=lambda row: (-row[0], row[3]["id"]))
    hits = scored[:max(1, k)]

    # retrieval is itself recorded: being retrieved without being credited is
    # what later marks an entry as merely familiar
    for _, _, _, entry in hits:
        rec = state["entries"].get(entry["id"])
        if rec is not None:
            rec["accesses"] = int(rec.get("accesses") or 0) + 1
            rec["last_accessed"] = now
    if hits:
        _save(state, path)
    return [{**e, "relevance": round(r, 6), "importance": round(i, 6),
             "score": round(s, 6)} for s, r, i, e in hits]


def credit(entry_id: str, *, helped: bool = True,
           path: str = DEFAULT_STATE) -> bool:
    """The consequence signal: did retrieving this actually help?

    This is the only thing that makes something important. Without it the
    memory is a search index.
    """
    state = _load(path)
    entry = state["entries"].get(entry_id)
    if entry is None:
        return False
    if helped:
        entry["credited"] = int(entry.get("credited") or 0) + 1
    else:
        entry["blamed"] = int(entry.get("blamed") or 0) + 1
    entry["last_accessed"] = _now()
    _save(state, path)
    return True


def forget(*, capacity: int = DEFAULT_CAPACITY, path: str = DEFAULT_STATE) -> list[str]:
    """Drop the least important entries once capacity is exceeded.

    What goes is decided by earned importance, not by age and not by insertion
    order. A memory that evicts oldest-first throws away everything it learned
    early, which is precisely the opposite of what a creature should do.
    """
    state = _load(path)
    entries = state["entries"]
    if len(entries) <= max(0, capacity):
        return []
    now = _now()
    ranked = sorted(entries.values(), key=lambda e: (importance(e, now=now), e["id"]))
    drop = [e["id"] for e in ranked[: len(entries) - capacity]]
    for eid in drop:
        entries.pop(eid, None)
    _save(state, path)
    return drop


def stats(path: str = DEFAULT_STATE) -> dict[str, Any]:
    state = _load(path)
    entries = list(state["entries"].values())
    now = _now()
    imps = [importance(e, now=now) for e in entries]
    return {
        "schema": SCHEMA,
        "count": len(entries),
        "credited": sum(1 for e in entries if e.get("credited")),
        "blamed": sum(1 for e in entries if e.get("blamed")),
        "mean_importance": (sum(imps) / len(imps)) if imps else 0.0,
        "max_importance": max(imps) if imps else 0.0,
    }
