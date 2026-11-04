#!/usr/bin/env python3
"""Does a moving world surprise it once, or every tick? Measured, not asserted.

A deterministic world cannot teach anything, so every clean run of the organism reports
`surprises 0` and proves nothing about learning. This tool moves the world under a running
organism, in one continuous life, and counts.

    phase 1  healthy world            the adapter honours the inputs it was given
    phase 2  world silently changes   the adapter regains the filter that drops plain
                                      repository files -- the exact defect of 2026-11-04
    phase 3  same changed world       nothing touched: a learner must stop being surprised
    phase 4  world restored           the old world is news again

What the first version of this experiment found, and what it forced:

  * run 1 (2026-11-04, before `_still_asleep`): the organism retired every target, rested,
    and `live()` stopped after MAX_IDLE_TICKS. The world was broken underneath it and it
    never looked. Rest had become permanent ignorance.
  * run 2 (after waking): the world churned under it 3 times and it was surprised 3 times,
    and 4 for the restoration, because it predicted from the modal verdict of the target's
    whole life. One change must cost one surprise; a lifetime average is a memory of a dead
    world.
  * run 3 (recency-weighted expectation): 1 surprise per change, 0 across the unchanged
    phases.

Usage:  python -m canonical.tools.organism_hostile_world_v1 [--ticks 34] [--write]
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import organism_v1 as org                       # noqa: E402

ADAPTER = ROOT / "canonical/runtime/bound_capabilities/archive_tarfile.py"
OUT = ROOT / "canonical/verification/ORGANISM_HOSTILE_WORLD_V1.json"
ANCHOR = '            if not isinstance(p,str) or not p.strip():\n'
BROKEN = ('            if not isinstance(p,str) or not p.strip():\n'
          '                continue\n'
          '            if not p.startswith("canonical/"):\n'
          '                continue\n')


def set_world(original: str, broken: bool) -> None:
    ADAPTER.write_text(original.replace(ANCHOR, BROKEN, 1) if broken else original,
                       encoding="utf-8")
    for name in [m for m in sys.modules if "archive_tarfile" in m]:
        del sys.modules[name]
    importlib.invalidate_caches()


def phase(label: str, ticks: int) -> dict:
    before = org.summary(org.load_state())
    org.live(ticks=ticks, interval=0.0, verbose=False)
    after = org.summary(org.load_state())
    delta = {k: (after[k] or 0) - (before[k] or 0)
             for k in ("actions", "predicted", "surprises", "idle_ticks")}
    print(f"  {label:32s} actions +{delta['actions']:2d}  predicted +{delta['predicted']:2d}  "
          f"surprises +{delta['surprises']:2d}  idle +{delta['idle_ticks']:2d}")
    return {"phase": label, "ticks_budget": ticks, **delta}


def run(ticks: int = 34, write: bool = False) -> dict:
    original = ADAPTER.read_text(encoding="utf-8")
    org.STATE.unlink(missing_ok=True)
    phases: list[dict] = []
    try:
        print("phase 1: healthy world")
        set_world(original, False)
        phases.append(phase("healthy_world", ticks))
        print("phase 2: the world changes under it (plain paths silently dropped)")
        set_world(original, True)
        phases.append(phase("world_changed", ticks))
        print("phase 3: changed world, untouched")
        phases.append(phase("world_unchanged", ticks))
        print("phase 4: world restored")
        set_world(original, False)
        phases.append(phase("world_restored", ticks))
    finally:
        set_world(original, False)
    summary = org.summary(org.load_state())
    unchanged = sum(p["actions"] for p in phases if p["phase"] in ("healthy_world", "world_unchanged"))
    unchanged_surprises = sum(p["surprises"] for p in phases
                              if p["phase"] in ("healthy_world", "world_unchanged"))
    moved = [p for p in phases if p["phase"] in ("world_changed", "world_restored")]
    doc = {
        "schema": "PROJECT_BRAIN_ORGANISM_HOSTILE_WORLD_V1",
        "question": "Does a change in the world cost it one surprise, and does an unchanged "
                    "world cost it none?",
        "phases": phases,
        "learning": {
            "surprises_per_world_change": [p["surprises"] for p in moved],
            "actions_while_world_unchanged": unchanged,
            "surprises_while_world_unchanged": unchanged_surprises,
            "surprise_early": summary["surprise_early"],
            "surprise_late": summary["surprise_late"],
        },
        "headline": {
            "surprises_per_world_change": max([p["surprises"] for p in moved] or [0]),
            "surprises_when_world_did_not_move": unchanged_surprises,
        },
        "history": [
            {"run": "before_waking", "result": "slept through the breakage: 0 surprises, 0 actions"},
            {"run": "after_waking_flat_history", "result": "3 surprises for one change, 4 for the "
                                                       "restoration (lifetime modal verdict)"},
            {"run": "recency_weighted_expected", "result": "1 surprise per change"},
        ],
        "non_claims": [
            "SURPRISE_IS_ABOUT_ITS_OWN_PREDICTIONS_NOT_CONSCIOUSNESS",
            "ONE_TARGET_ONE_ADAPTER_IS_NOT_A_GENERAL_WORLD",
            "THE_ORGANISM_MAY_NOT_ADD_ORGANS_TO_ITSELF",
            "SURPRISE_FALLING_TO_ZERO_WHILE_THE_WORLD_MOVES_WOULD_BE_INDIFFERENCE_NOT_LEARNING",
        ],
        "authority": "NO_CAPABILITY_CREDIT_MEASUREMENT_ONLY",
        "summary": summary,
    }
    print("\nRESULT")
    print(f"  surprises per world change : {doc['headline']['surprises_per_world_change']}")
    print(f"  surprises, world unchanged : {doc['headline']['surprises_when_world_did_not_move']}"
          f" over {unchanged} actions")
    print(f"  surprise early {summary['surprise_early']} -> late {summary['surprise_late']}")
    if write:
        OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"  wrote {OUT.relative_to(ROOT)}")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=34)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    doc = run(ticks=args.ticks, write=args.write)
    gate = (doc["headline"]["surprises_per_world_change"] == 1
            and doc["headline"]["surprises_when_world_did_not_move"] == 0)
    print("VERDICT", "ONE_SURPRISE_PER_CHANGE" if gate else "NOT_LEARNING")
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
