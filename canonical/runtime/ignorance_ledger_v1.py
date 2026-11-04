#!/usr/bin/env python3
"""The machine's own model of what it does not know, ranked by what it is worth.

"Knows what needs to be known" is the part that is not a strict program. A
program is told what to fetch and in what order. A creature looks at everything
it is missing, decides which absence is actually costing it, and goes after that
one first -- and gets better at that judgement by being wrong sometimes.

This is a ledger of gaps, each ranked by expected value of closing it:

    p_useful = (times closing it helped + 0.5) / (times tried + 1)
    value    = p_useful / (1 + cost)

Three properties fall out of that, none of them programmed as rules:

  EXPLORATION IS FREE. An untried gap scores 0.5 -- maximum uncertainty. A gap
  tried ten times and never useful scores 0.045. So the machine prefers the
  unknown over the known-useless without anyone writing an exploration rule.
  The prior does it.

  IT LEARNS WHICH KINDS OF IGNORANCE MATTER. Some gaps -- "only one independent
  channel" -- turn out to block everything. Others never matter. The ledger
  discovers which, from outcomes, and reorders itself.

  COST COUNTS. A gap worth 0.9 that takes an hour loses to one worth 0.6 that
  takes a second, because the question is not "what is most valuable" but "what
  is most valuable per unit of the time I am spending".

Nothing here enumerates what to learn. It only says: of the things you have
noticed you do not know, try this one next, and tell me whether it helped.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_IGNORANCE_LEDGER_V1"

DEFAULT_STATE = str(
    Path(__file__).resolve().parents[2]
    / "canonical/astra_runtime/state/IGNORANCE_LEDGER_V1.json"
)

_WORD = re.compile(r"[a-z0-9]{2,}")


def _beta_mean(successes: int, trials: int) -> float:
    """Laplace-smoothed rate. Untried is 0.5, not 0 -- see module docstring."""
    trials = max(0, int(trials))
    successes = max(0, min(trials, int(successes)))
    return (successes + 0.5) / (trials + 1.0)


def _identity(what: str, why: str) -> str:
    """The ledger's existing normalized-token definition of a gap."""
    text = f"{what} {why}".lower()
    return "|".join(sorted(set(_WORD.findall(text))))


def _key(what: str, why: str) -> str:
    """A stable ID for that identity, independent of Python's per-process hash seed.

    Normalized token overlap is only this ledger's identity heuristic, not a
    proof that two questions are semantically equivalent.
    """
    return "g" + hashlib.sha256(_identity(what, why).encode("utf-8")).hexdigest()


def _load(path: str = DEFAULT_STATE) -> dict:
    from canonical.runtime.memory_policy_v1 import can_read_memory

    if not can_read_memory():
        return {"schema": SCHEMA, "gaps": {}}
    p = Path(path)
    if not p.exists():
        return {"schema": SCHEMA, "gaps": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("schema") == SCHEMA:
            data.setdefault("gaps", {})
            return data
    except (OSError, ValueError):
        pass
    return {"schema": SCHEMA, "gaps": {}}


def _save(state: dict, path: str = DEFAULT_STATE) -> None:
    from canonical.runtime.memory_policy_v1 import can_write_memory

    if not can_write_memory():
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def note(what: str, *, why: str = "", cost: float = 1.0,
         path: str | None = None) -> str:
    """Notice something you do not know. Returns the gap id."""
    path = path or DEFAULT_STATE
    state = _load(path)
    identity = _identity(what, why)
    gid = _key(what, why)
    gap = state["gaps"].get(gid)
    if gap is not None and (not isinstance(gap, Mapping)
                            or _identity(gap.get("what", ""), gap.get("why", "")) != identity):
        raise ValueError("IGNORANCE_GAP_IDENTITY_CONFLICT")
    if gap is None:
        # Older files contain numeric IDs made with Python's randomized hash.
        # Reuse an existing matching row without changing its ID, counters or
        # references. Already-duplicated legacy rows are not merged or deleted.
        matches = sorted(k for k, row in state["gaps"].items()
                         if isinstance(row, Mapping)
                         and _identity(row.get("what", ""), row.get("why", "")) == identity)
        if matches:
            gid = matches[0]
            gap = state["gaps"][gid]
    now = time.time()
    if gap is None:
        gap = {"id": gid, "what": str(what), "why": str(why),
               "cost": float(cost), "trials": 0, "helped": 0,
               "created": now, "last_seen": now, "resolved": False}
        state["gaps"][gid] = gap
    else:
        # seen again: it is still open, and the newest phrasing is the clearest
        gap["last_seen"] = now
        gap["what"] = str(what)
        gap["why"] = str(why)
        # Seeing the same gap again is new evidence that it is open now;
        # preserve the past outcomes rather than treating them as a cure.
        gap["resolved"] = False
        if cost:
            gap["cost"] = float(cost)
    _save(state, path)
    return gid


def value(gap: Mapping[str, Any]) -> float:
    """Expected value of closing this gap, per unit cost."""
    p = _beta_mean(int(gap.get("helped") or 0), int(gap.get("trials") or 0))
    return p / (1.0 + max(0.0, float(gap.get("cost") or 0.0)))


def rank(*, limit: int = 5, include_resolved: bool = False,
         path: str | None = None) -> list[dict[str, Any]]:
    """What to learn next, in the order it is worth learning.

    Ordered by expected value, and that order is LEARNED -- it changes as the
    machine finds out which gaps actually paid off. Nothing here hardcodes
    "check sources first" or any other sequence.
    """
    path = path or DEFAULT_STATE
    state = _load(path)
    gaps = [g for g in state["gaps"].values()
            if include_resolved or not g.get("resolved")]
    scored = [(value(g), g) for g in gaps]
    # ties break toward the least-tried: with equal value, prefer learning
    # something new over re-confirming something known
    scored.sort(key=lambda row: (-row[0], int(row[1].get("trials") or 0), row[1]["id"]))
    return [{**g, "p_useful": round(_beta_mean(int(g.get("helped") or 0),
                                               int(g.get("trials") or 0)), 6),
             "value": round(v, 6)} for v, g in scored[:max(1, limit)]]


def resolve(gap_id: str, *, helped: bool = True, close: bool = True,
            path: str | None = None) -> bool:
    """Record whether closing this gap actually helped.

    This is the only thing that teaches the ledger which ignorance matters.
    Without it, rank() is a guess dressed up as a calculation.
    """
    path = path or DEFAULT_STATE
    state = _load(path)
    gap = state["gaps"].get(gap_id)
    if gap is None:
        return False
    gap["trials"] = int(gap.get("trials") or 0) + 1
    if helped:
        gap["helped"] = int(gap.get("helped") or 0) + 1
    # `close and helped`, and that is CORRECT -- nearly changed, and the existing
    # `test_failed_attempt_leaves_it_open` caught it. If closing a gap did not help, the
    # doubt is STILL THERE; only its expected value drops, because `trials` rose and
    # `helped` did not. `resolved` means the doubt is gone. A failed attempt is not a cure,
    # and recording it as one would empty the ledger of exactly the gaps it should chase.
    if close and helped:
        gap["resolved"] = True
    gap["last_seen"] = time.time()
    _save(state, path)
    return True


def open_gaps(path: str | None = None) -> int:
    return sum(1 for g in _load(path or DEFAULT_STATE)["gaps"].values()
               if not g.get("resolved"))


def stats(path: str | None = None) -> dict[str, Any]:
    gaps = list(_load(path or DEFAULT_STATE)["gaps"].values())
    tried = [g for g in gaps if int(g.get("trials") or 0) > 0]
    return {
        "schema": SCHEMA,
        "gaps": len(gaps),
        "open": sum(1 for g in gaps if not g.get("resolved")),
        "resolved": sum(1 for g in gaps if g.get("resolved")),
        "tried": len(tried),
        "ever_helped": sum(1 for g in tried if int(g.get("helped") or 0) > 0),
    }
