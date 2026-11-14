#!/usr/bin/env python3
"""The round's instrument: measure what a taught edit becomes observable as, on real pairs.

Run:
    python3 canonical/tools/observable_surface_on_new_pull_requests_20261114_v1.py \
        --pulls canonical/tests/fixtures/fresh_heldout_pulls_20261114.json \
        --json canonical/verification/OBSERVABLE_SURFACE_ON_NEW_PULL_REQUESTS_20261114_V1.json

It replays the same 230 pairs of the already-committed record, keeps the 44 the taught-edit organ
actually altered, and for each one asks the widened observer (`observable_surface_v1`) what the edit
moved. Nothing here calls a model, a network, or a test harness. $0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import observable_surface_v1 as surfaces          # noqa: E402
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as taught  # noqa: E402
from canonical.tools import oracle_active_on_new_pull_requests_20261114_v1 as old  # noqa: E402

SCHEMA = "BRAIN_OBSERVABLE_SURFACE_MEASURE_V1"


def measure(pulls: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for pull in pulls:
        files = pull["files"]
        for index, example in enumerate(files):
            for other, target in enumerate(files):
                if index == other:
                    continue
                try:
                    edited = taught.edit_by_example(target["before"], example["before"],
                                                    example["after"])
                except Exception:                               # noqa: BLE001 - a refusal
                    continue
                if edited is None or edited == target["before"]:
                    continue
                # The already-committed reader: one loadable top-level function on both sides.
                reachable_before = (old._load(target["before"]) is not None
                                    and old._load(edited) is not None)
                row = {"pull": pull["name"], "path": target["path"],
                       "old_reader_reached": bool(reachable_before)}
                for name, strict in (("strict", True), ("lenient", False)):
                    comparison = surfaces.comparable(
                        surfaces.observe(target["before"], strict=strict),
                        surfaces.observe(edited, strict=strict))
                    row[name] = {
                        "behaviour": comparison["behaviour_differences"],
                        "declaration": comparison["declaration_differences"],
                        "surfaces_before": comparison["reached_before"],
                        "surfaces_after": comparison["reached_after"],
                    }
                rows.append(row)

    def seen(name: str, subset: list[dict[str, Any]]) -> int:
        return sum(1 for r in subset if r[name]["behaviour"] + r[name]["declaration"] > 0)

    new = [r for r in rows if not r["old_reader_reached"]]
    known = [r for r in rows if r["old_reader_reached"]]
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "pulls": len(pulls),
        "pairs_the_organ_altered": len(rows),
        "per_pair": rows,
        "summary": {
            "old_reader_reached": len(known),
            "old_reader_did_not_reach": len(new),
            "newly_seen": {n: seen(n, new) for n in ("strict", "lenient")},
            "still_unseen": len(new) - seen("strict", new),
            "seen_among_the_old_25": {n: seen(n, known) for n in ("strict", "lenient")},
            "behaviour_vs_declaration": {
                n: {
                    "behaviour_only_pairs": sum(1 for r in rows
                                                if r[n]["behaviour"] > 0 and r[n]["declaration"] == 0),
                    "declaration_only_pairs": sum(1 for r in rows
                                                  if r[n]["declaration"] > 0 and r[n]["behaviour"] == 0),
                    "both": sum(1 for r in rows
                                if r[n]["behaviour"] > 0 and r[n]["declaration"] > 0),
                    "neither": sum(1 for r in rows
                                   if r[n]["behaviour"] == 0 and r[n]["declaration"] == 0),
                }
                for n in ("strict", "lenient")
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    record = measure(json.loads(args.pulls.read_text()))
    text = json.dumps(record, indent=1)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n")
        print("written ->", args.json)
        print(json.dumps(record["summary"], indent=1))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
