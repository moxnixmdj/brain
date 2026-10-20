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


def _key(what: str, why: str) -> str:
    """Gaps that mean the same thing are the same gap, however phrased."""
    text = f"{what} {why}".lower()
    terms = sorted({w for w in _WORD.findall(text)})
    return "g" + str(abs(hash("|".join(terms))) % (1 << 40))


def _load(path: str = DEFAULT_STATE) -> dict:
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
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def note(what: str, *, why: str = "", cost: float = 1.0,
         path: str | None = None) -> str:
    """Notice something you do not know. Returns the gap id."""
    path = path or DEFAULT_STATE
    state = _load(path)
    gid = _key(what, why)
    now = time.time()
    gap = state["gaps"].get(gid)
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
