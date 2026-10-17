"""Generate options without guessing.

The grounding matched goals to capabilities by shared vocabulary. Two of three
real goals produced nothing, and the one match it did produce was a capability
that could not act on the goal.

This ignores wording completely and asks a different question:

    what can I actually DO with what I already hold?

A capability is an option when every input it declares is something we can
supply. We can always create an output path. Anything else must already be in
hand -- a fact we can check, not guess.

Ranking is by reach: how many NEW things does running it make available?
A capability that unlocks more downstream work is more valuable than one
that terminates, which is a judgement about capability rather than about
names.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))

import capability_composer_v1 as COMPOSER  # noqa: E402

SCHEMA = "PROJECT_BRAIN_OPTIONS_V1"

# Types we can conjure by deciding to. Everything else must be supplied.
SELF_PRODUCIBLE = {"PATH_OUTPUT"}


def fillable(holding: set[str], sig: dict[str, str]) -> tuple[bool, list[str]]:
    """Can we call this capability, and what is still missing?"""
    missing = []
    for name, typ in (sig or {}).items():
        if typ in SELF_PRODUCIBLE:
            continue
        if name in holding or typ in holding:
            continue
        missing.append(name)
    return (not missing), missing


def options(holding: set[str] | None = None, limit: int = 12) -> list[dict]:
    """Every capability we could call right now, ranked by what it unlocks."""
    holding = set(holding or ())
    reg = COMPOSER.load_registry()
    rows = []
    for cid, entry in reg.items():
        sig = COMPOSER.signature(cid)
        if not sig:
            continue  # fixed-task capability: cannot act on a caller's request
        ok, missing = fillable(holding, sig)
        if not ok:
            continue
        provides = list(entry.get("provides") or [])
        rows.append({
            "capability_id": cid,
            "declared_inputs": sig,
            "provides": provides,
            "reach": len(provides),
            "cost": entry.get("cost", 1),
        })
    rows.sort(key=lambda r: (-r["reach"], r["cost"], r["capability_id"]))
    return rows[:limit]


if __name__ == "__main__":
    import json
    held = set(sys.argv[1:])
    rows = options(held)
    print(f"holding: {sorted(held) or '(nothing)'}")
    print(f"actionable capabilities: {len(rows)}")
    for r in rows:
        print(f"  reach={r['reach']:<2} {r['capability_id']:<52} "
              f"provides={r['provides'][:2]}")
