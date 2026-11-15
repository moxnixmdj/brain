#!/usr/bin/env python3
"""Is the wall selection, expression, or composition? One measurement decides what goes in the weights.

WHY THIS EXISTS
---------------
Three rounds have separated failure modes that look identical from the outside:

  SELECTION    a correct lesson was in the pool and the organ ranked another first.
  EXPRESSION   the pool can shape the change but cannot fill it -- right form, wrong content.
  COMPOSITION  the edit is not one substitution at all.

Only the first is a ranking problem. The second is what the 2026 literature says weights exist for
("only encoding the composition rule into weights resolves the gap entirely", arXiv:2604.27707).
The third is a different claim again, and this round measured it and it dominates.

THE ARITHMETIC THAT MAKES IT DECIDE SOMETHING
---------------------------------------------
If a lesson is a substitution that lands with probability `p`, and a real edit needs `k` independent
substitutions to be right together, then:

    per file    p**k
    per task    p**(k * files)

so learning a substitution faster raises `p` and leaves `k` alone -- and `k` is a property of the
edit, not of the learner. That is why "let it do each action once and it learns it" cannot reach a
task by getting faster: the exponent is not in the part being learned.

WHAT IS MEASURED
----------------
For every real changed file in the held-out corpus, offered every other changed file in all eight
repositories as a demonstration:

  oracle_selector      can ANY lesson in the pool produce the developers' text exactly
  shaped_not_filled    a candidate was produced and it is not what the developers wrote
  produced_nothing     the organ refused every lesson
  dev_hunks            separate places the developers changed
  org_hunks            separate places the organ changed

Authority: NONE. $0, no model calls, no network.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as taught   # noqa: E402

SCHEMA = "BRAIN_COMPOSITION_GAP_V1"
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def _hunks(before: str, after: str) -> int:
    """Separate places one text differs from another."""
    return sum(1 for line in difflib.unified_diff(before.splitlines(), after.splitlines(),
                                                  n=0, lineterm="") if line.startswith("@@"))


def measure(pulls: list[dict[str, Any]]) -> dict[str, Any]:
    demos = [f for p in pulls for f in p["files"] if f["before"] != f["after"]]
    rows = []
    for pull in pulls:
        for target in pull["files"]:
            if target["before"] == target["after"]:
                continue
            exact = False
            shaped = produced = 0
            closest: str | None = None
            for demo in demos:
                if demo is target:
                    continue
                try:
                    edited = taught.edit_by_example(target["before"], demo["before"],
                                                    demo["after"])
                except Exception:                                # noqa: BLE001 - a refusal
                    continue
                if edited is None or edited == target["before"]:
                    continue
                produced += 1
                if edited == target["after"]:
                    exact = True
                    break
                shaped += 1
                closest = edited
            rows.append({
                "pull": pull["name"], "path": target["path"], "exact": exact,
                "candidates_produced": produced,
                "shaped_not_filled": shaped > 0 and not exact,
                "produced_nothing": produced == 0,
                "dev_hunks": _hunks(target["before"], target["after"]),
                "org_hunks": _hunks(target["before"], closest) if closest else 0,
                "dev_names_beyond_the_example": len(
                    {n for n in NAME.findall(target["after"])} - {n for n in NAME.findall(target["before"])}),
            })
    n = len(rows)
    exact = sum(r["exact"] for r in rows)
    shaped = sum(1 for r in rows if r["shaped_not_filled"])
    nothing = sum(1 for r in rows if r["produced_nothing"])
    partial = sum(1 for r in rows if r["shaped_not_filled"] and r["org_hunks"] < r["dev_hunks"])
    coordinated = sum(1 for r in rows if r["dev_hunks"] > 1)
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "targets": n,
        "oracle_selector": {"exact": exact, "share": round(exact / n, 4) if n else 0.0,
                            "reading": "a perfect ranking over this lesson pool, nothing else changed"},
        "shaped_not_filled": shaped,
        "produced_nothing": nothing,
        "single_substitution_edits": n - coordinated,
        "coordinated_edits": coordinated,
        "organ_applied_fewer_changes_than_the_developers": partial,
        "the_arithmetic": {
            "reading": "a real edit needs k independent substitutions to be right together; a lesson "
                       "raises p and cannot lower k, and a task multiplies the exponent by its files",
            "measured_exact_share": round(exact / n, 4) if n else 0.0,
        },
        "per_target": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    record = measure(json.loads(args.pulls.read_text()))
    text = json.dumps(record, indent=1)
    if args.json:
        args.json.write_text(text + "\n")
        print("written ->", args.json)
        print(json.dumps({k: v for k, v in record.items()
                          if k not in ("per_target", "schema")}, indent=1))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
