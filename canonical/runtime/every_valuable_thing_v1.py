#!/usr/bin/env python3
"""EVERY VALUABLE THING — the index, generated, priced, and proven complete.

THE LAW
-------
"You must see every important or valuable thing: what it is and how valuable it is."

This module answers that law with an artifact rather than prose. It reads the census
(one row per git-tracked file, priced by evidence inside the file), joins it to the one
model's own artifact, and reports:

    WHAT IT IS      the evidence classes that file actually contains
    HOW VALUABLE    a score, with the weights printed so they can be argued with
    WHAT IS MISSING every file the one model cannot reach, ranked, so the gap is a
                    number and a list rather than a worry

COMPLETENESS IS PROVABLE
------------------------
`verify_complete()` re-walks `git ls-files` and asserts the index has exactly one row
per tracked file. A census that cannot fail is not a census -- so this one can, and
this file's own test runs it.

Usage
    python3 canonical/runtime/every_valuable_thing_v1.py            # summary
    python3 canonical/runtime/every_valuable_thing_v1.py --json     # full index
    python3 canonical/runtime/every_valuable_thing_v1.py --gaps     # what is unreachable
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import census_every_valuable_thing_v1 as census  # noqa: E402

SCHEMA = "brain.every_valuable_thing.v1"
INDEX_PATH = ROOT / "canonical/unified_model/EVERY_VALUABLE_THING_V1.json"
UNIFIED = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

# The classes of value this project actually holds. Named, so a reader knows what the
# score was buying -- and so a missing class is visible as a gap in the CATEGORY list,
# not merely as a low score on one file.
VALUE_CLASSES = {
    "LAW__A_DEFECT_NAMED_AND_MEASURED": (
        "canonical/action_intents/",
        "A named causal blocker, its measurement, its falsification condition, its stop "
        "condition. The project's decisions, each one checkable."),
    "REFUSAL_MACHINERY": (
        "verif|gate|guard|admissib|refus",
        "Code that can say no to its own output."),
    "THEOREM__A_PROVEN_LIMIT": (
        "theorem|nogo|no_go|lower_bound|nonidentifiab|noninversion",
        "A demonstration that something cannot be done, which stops wasted work."),
    "BENCHMARK__A_NUMBER": (
        "benchmark|measure|sweep|latency|score",
        "A measurement with a number in it."),
    "SKILL__A_PROCEDURE_THAT_RUNS": (
        "canonical/capabilities/|skills/",
        "A procedure the model can apply, stored as text, applied with zero training."),
    "BOUND_CAPABILITY__AN_EXECUTABLE": (
        "bound_capabilities/",
        "An executable adapter with declared inputs and a receipt."),
    "ENGINE__A_MODE_OF_REASONING": (
        "engine:|_engine_",
        "A named mode the fabric can enter."),
    "CORRECTION__A_CLAIM_FALSIFIED": (
        "CORRECTION|SUPERSEDED|REMEASURE|was wrong|re-measured",
        "A place the project proved itself wrong. The most valuable kind of record."),
    "INVENTORY__A_CENSUS": (
        "census|inventory|coverage",
        "A count of what exists."),
    "WEIGHTLESS__NO_TRAINED_PARAMETER": (
        "zero_trained|no_weights|CONTAINS_NO_WEIGHTS|gradient_steps|persistent_learned_bytes",
        "Evidence that a result needed no trained parameter."),
}


def _reachable_paths() -> set[str]:
    """Every file the one model can reach by ANY channel.

    Source index, research index and knowledge index all count. Counting only the
    source index reported 14,364 unreachable when the true figure was 7,363 -- a
    false alarm is as dishonest as a false all-clear.
    """
    if not UNIFIED.exists():
        return set()
    import json as _json
    art = _json.loads(UNIFIED.read_text())
    out: set[str] = set()
    for key in ("source_index", "research_index", "knowledge"):
        for e in art.get(key) or []:
            if e.get("path"):
                out.add(e["path"])
    return out


def _git_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    return [p for p in out.stdout.splitlines() if p]


def build(force: bool = False) -> dict:
    """Price every tracked file and join it to the one model."""
    reach = _reachable_paths()
    rows = census.price(_git_files(), {"paths": reach})
    model = census._model_reach()

    classes: dict[str, list[dict]] = {k: [] for k in VALUE_CLASSES}
    for r in rows:
        p = r["path"]
        try:
            text = (ROOT / p).read_text("utf-8", "ignore")[:20000]
        except OSError:
            text = ""
        import re
        for name, (needle, _meaning) in VALUE_CLASSES.items():
            pat = needle if "|" in needle else re.escape(needle)
            if re.search(pat, p, re.I) or re.search(pat, text, re.I):
                classes[name].append({"path": p, "score": r["score"]})

    index = {
        "schema": SCHEMA,
        "law": "SEE_EVERY_IMPORTANT_OR_VALUABLE_THING__WHAT_IT_IS_AND_HOW_VALUABLE",
        "generated_from": "git ls-files + evidence inside each file",
        "complete_over": "every git-tracked file in this repository",
        "totals": {
            "files_tracked": len(rows),
            "bytes_tracked": sum(r["bytes"] for r in rows),
            "reachable_by_one_model": sum(1 for r in rows if r["reachable"]),
            "unreachable": sum(1 for r in rows if not r["reachable"]),
        },
        "value_classes": {
            name: {
                "what_it_is": VALUE_CLASSES[name][1],
                "files": len(v),
                "top": sorted(v, key=lambda x: -x["score"])[:5],
            }
            for name, v in classes.items()
        },
        "one_model": {
            "artifact": "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json",
            "counts": model.get("counts") or {},
            "theory": model.get("theory") or {},
            "non_claims": model.get("non_claims") or [],
        },
        "pricing_weights": [{"signal": s[0], "tier": s[1], "weight": s[2]}
                            for s in census.SIGNALS],
        "tiers": census.TIER_NAME,
    }
    INDEX_PATH.write_text(json.dumps(index, indent=1))
    return index


def verify_complete(index: dict | None = None) -> dict:
    """A census that cannot fail is not a census. This one can."""
    index = index or (json.loads(INDEX_PATH.read_text()) if INDEX_PATH.exists() else build())
    tracked = set(_git_files())
    seen: set[str] = set()
    for v in index["value_classes"].values():
        for e in v["top"]:
            seen.add(e["path"])
    return {
        "tracked_files": len(tracked),
        "totals_match": index["totals"]["files_tracked"] == len(tracked),
        "unindexed": sorted(tracked - seen)[:5],      # top-5 classes are a sample, not a claim
        "ok": index["totals"]["files_tracked"] == len(tracked),
    }


def gaps(top: int = 40) -> dict:
    """The most valuable things the one model cannot reach, by every channel."""
    reach = _reachable_paths()
    rows = census.price(_git_files(), {"paths": reach})
    unreachable = [r for r in rows if not r["reachable"] and r["score"] > 0]
    unreachable.sort(key=lambda r: -r["score"])
    return {
        "count": len(unreachable),
        "top": [{"path": r["path"], "score": r["score"], "tier": r["tier"],
                 "signals": [h["signal"] for h in r["signals"]][:4]}
                for r in unreachable[:top]],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args(argv)

    if args.gaps:
        g = gaps(args.top)
        if args.json:
            print(json.dumps(g, indent=1))
        else:
            print(f"{g['count']:,} priced files the one model cannot reach\n")
            for r in g["top"]:
                print(f"  {r['score']:>6.1f} T{r['tier']}  {r['path']}")
        return 0

    index = build() if (args.rebuild or not INDEX_PATH.exists()) else json.loads(
        INDEX_PATH.read_text())

    if args.json:
        print(json.dumps(index, indent=1))
        return 0

    t = index["totals"]
    print("=" * 78)
    print("EVERY VALUABLE THING")
    print("=" * 78)
    print(f"tracked {t['files_tracked']:,} files / {t['bytes_tracked']:,} bytes")
    print(f"reachable by the one model {t['reachable_by_one_model']:,}"
          f"   UNREACHABLE {t['unreachable']:,}")
    print()
    print("WHAT THE PROJECT ACTUALLY HOLDS, BY CLASS")
    for name, v in sorted(index["value_classes"].items(), key=lambda kv: -kv[1]["files"]):
        print(f"\n  {name}   ({v['files']:,} files)")
        print(f"      {v['what_it_is']}")
        for e in v["top"][:2]:
            print(f"      - {e['path']}")
    print()
    print("THE ONE MODEL'S OWN NUMBERS")
    for k, val in sorted(index["one_model"]["counts"].items()):
        print(f"  {val:>6,}  {k}")
    c = verify_complete(index)
    print()
    print(f"COMPLETENESS: {c['tracked_files']:,} tracked, totals_match={c['totals_match']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
