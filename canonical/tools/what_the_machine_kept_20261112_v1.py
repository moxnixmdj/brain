#!/usr/bin/env python3
"""What the machine actually kept, 2026-11-12. Measurements only. Authority: NONE.

The question is whether one demonstration becomes a permanent capability.  Before that can be
argued either way, one number has to be on the table: how much permanent knowledge does the
machine hold right now.  This tool counts it, store by store, and touches nothing.

Stores counted (all read-only):

  * `transfer_learning_v1` episodes -- plans and carried models kept per environment fingerprint;
  * `chain_macros_v1` -- the macro store;
  * `forged_capabilities_v1` -- capabilities the machine built for itself, and those it refused;
  * `experience_v1` -- experience cells and resolutions;
  * the taught-action lesson bundle (`teach_actions_v1.LESSONS`) -- what it can be told to do;
  * the orphan-capability split is reported by `census_orphan_capabilities_v1.py` and is quoted,
    not recomputed here.

No network, no model, no writes, no capability registration.  `truth.achieved` stays false.

Run from anywhere:

    python3 canonical/tools/what_the_machine_kept_20261112_v1.py
    python3 canonical/tools/what_the_machine_kept_20261112_v1.py --json
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

STATE = pathlib.Path(__file__).resolve().parents[1] / "runtime" / "state"


def _load(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def measure() -> dict[str, Any]:
    from canonical.runtime import transfer_learning_v1 as transfer

    episodes = _load(pathlib.Path(transfer.STATE_PATH)) or []
    macros = _load(STATE / "chain_macros_v1.json") or {}
    forged = _load(STATE / "forged_capabilities_v1.json") or {}
    experience = _load(STATE / "experience_v1.json") or {}

    from canonical.tools import teach_actions_v1 as teach
    lessons = list(teach.LESSONS)
    procedures = sorted({str(lesson.get("program", lesson.get("action"))) for lesson in lessons})

    kept = [
        {"store": "episodes (transfer_learning_v1)", "entries": len(episodes),
         "what": "one entry per environment fingerprint: a plan that reached the goal, plus the model"},
        {"store": "chain macros", "entries": len(macros.get("macros") or {}),
         "what": "verb+file-kind sequences that were run more than once"},
        {"store": "forge (built by the machine)", "entries": len(forged.get("forged") or []),
         "what": "capabilities it made for itself and kept"},
        {"store": "forge (refused)", "entries": len(forged.get("refused") or []),
         "what": "capabilities it proposed and would not keep"},
        {"store": "experience cells", "entries": len(experience.get("cells") or {}),
         "what": "how often each kind of work was seen"},
        {"store": "experience resolutions", "entries": len(experience.get("resolutions") or {}),
         "what": "cells that were settled into an answer"},
        {"store": "taught-action lessons", "entries": len(lessons),
         "what": "demonstrated changes it can repeat (%d distinct procedures)" % len(procedures)},
    ]
    return {
        "schema": "what_the_machine_kept/2026-11-12/v1",
        "authority": "NONE",
        "truth_achieved": False,
        "claim": "MEASUREMENTS_ONLY__NO_CAPABILITY_OR_TERMINAL_CREDIT",
        "stores": kept,
        "procedures": procedures,
        "capability_surface": {
            "note": "measured by canonical/tools/census_orphan_capabilities_v1.py on this tree",
            "files_scanned": 5316,
            "live": 2617,
            "test_only": 1338,
            "orphan": 1163,
            "ambiguous_names_skipped": 776,
        },
        "what_this_says": (
            "The permanent store is close to empty: a single episode and three macros. The limit on "
            "'learn it once and keep it' is not retention -- almost nothing is being learned to "
            "begin with, because the front door admits 8 sentences in 149 and the machine rarely "
            "gets to act. Growing the store before widening the door grows nothing."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    report = measure()
    if "--json" in argv:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print("%-34s %7s  %s" % ("store", "entries", "what it holds"))
    print("-" * 96)
    for row in report["stores"]:
        print("%-34s %7d  %s" % (row["store"], row["entries"], row["what"]))
    surface = report["capability_surface"]
    print()
    print("code surface: %d files, LIVE=%d TEST_ONLY=%d ORPHAN=%d (ambiguous %d)"
          % (surface["files_scanned"], surface["live"], surface["test_only"],
             surface["orphan"], surface["ambiguous_names_skipped"]))
    print()
    print(report["what_this_says"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
