#!/usr/bin/env python3
"""Re-measure the door's own diagnoses, in a disposable clone, on the realistic corpus.

WHY THIS EXISTS
---------------
`canonical/tools/realistic_goal_reach_probe_v1.py` measures what the door DOES with 39 realistic
advanced-coding sentences and prints `status` -- the label.  It throws away `served_after`, which
is where the door records the reason it had already computed before a later branch spoke over it.

That omission is why 2026-11-12 could produce, on the same day and from the same tree:

  * `A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION`: "the dominant failure mode is BINDING,
    54 capabilities, 37%" (measured at `grounded_action_v1.act`);
  * `TWO_DOORS_COUNT_AVAILABILITY_DIFFERENTLY`: "no binding-shaped status exists at the door".

Both read the label.  This tool reads the reason underneath it, which is the only way to tell a
carrier problem from a binding problem from a request problem.

WHAT IT REPORTS
---------------
Per capability: `status` (what the caller saw) AND `served_after` (the decision that was made
first), plus `compiler_code`/`compiler_detail` where the compiler refused.  Then two aggregates:

  * `label_histogram`      -- what the published counts are made of;
  * `label_vs_reason`      -- for every row whose label is the carrier status, the reason it
                              replaced, or `NO_EARLIER_DECISION` when there was none;
  * `recovered_by_rule`    -- how many carrier rows a record-keeping repair (not a capability)
                              would report honestly, and how many must keep the carrier answer
                              because the earlier attempt may already have had effects.

WHAT IT DOES NOT DO
-------------------
No capability is registered.  No family flips.  No refusal is lifted -- this tool only reports
which refusal is firing.  It runs in a `git clone --no-local` (never the caller's tree) because
some of these rows really do write files.  Authority NONE.  $0.  Zero model dependency.

    python3 canonical/tools/which_refusal_is_actually_firing_v1.py
    python3 canonical/tools/which_refusal_is_actually_firing_v1.py --out /tmp/reasons.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_WHICH_REFUSAL_IS_ACTUALLY_FIRING_V1"
CARRIER = "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"

_KEYS = ("pass", "status", "served_after", "compiled_capability_id", "compiler_code",
         "compiler_detail", "failure_class", "executed", "side_effects_may_exist")


def _corpus() -> dict[str, str]:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "realistic_probe", ROOT / "canonical" / "tools" / "realistic_goal_reach_probe_v1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.CORPUS)


def _probe(clone: pathlib.Path, index: int, goal: str) -> dict:
    script = (
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "from canonical.runtime import live_brain_route_admission_v1 as door\n"
        "v = door.solve({'task_id': %r, 'goal': %r})\n"
        "print(json.dumps({k: v.get(k) for k in %r}))\n"
        % (str(clone), "reason_%d" % index, goal, _KEYS)
    )
    try:
        out = subprocess.run([sys.executable, "-c", script], cwd=str(clone),
                             capture_output=True, text=True, timeout=600)
        return json.loads((out.stdout.strip().splitlines() or ["{}"])[-1])
    except Exception as exc:  # noqa: BLE001 - a raise is a fate, recorded as one
        return {"status": "PROBE_RAISED:%s" % type(exc).__name__}


def _may_have_effects(row: dict) -> bool:
    return row.get("executed") is True or row.get("side_effects_may_exist") is True


def _would_be_kept(row: dict) -> bool:
    return (row.get("status") == CARRIER
            and str(row.get("served_after") or "") not in ("", "FAIL_CLOSED")
            and not _may_have_effects(row))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--clone", default="", help="use this existing clone instead of making one")
    args = ap.parse_args(argv)

    corpus = _corpus()
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        clone = pathlib.Path(args.clone) if args.clone else pathlib.Path(tmp) / "tree"
        if not args.clone:
            subprocess.run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(clone)],
                           check=True, capture_output=True)
        rows = []
        for i, cid in enumerate(sorted(corpus)):
            verdict = _probe(clone, i, corpus[cid])
            row = {"capability_id": cid}
            row.update({k: verdict.get(k) for k in _KEYS})
            for key in ("status", "served_after", "failure_class", "compiler_detail"):
                row[key] = str(row.get(key) or "")[:200]
            row["would_be_kept_by_record_keeping"] = _would_be_kept(row)
            row["must_keep_the_carrier_answer"] = row["status"] == CARRIER and _may_have_effects(row)
            rows.append(row)
            print("  %-52s %-62s %s" % (cid, row["status"][:62], row["served_after"][:50]),
                  flush=True)

    carrier_rows = [r for r in rows if r["status"] == CARRIER]
    report = {
        "schema": SCHEMA,
        "authority": "NONE",
        "incremental_spend_usd": 0,
        "model_dependency_count": 0,
        "clone_used": bool(args.clone),
        "corpus_size": len(rows),
        "label_histogram": dict(Counter(r["status"] for r in rows)),
        "label_vs_reason": {
            r["capability_id"]: (r["served_after"] or "NO_EARLIER_DECISION") for r in carrier_rows
        },
        "carrier_rows": len(carrier_rows),
        "carrier_rows_with_an_earlier_decision": sum(
            1 for r in carrier_rows if r["served_after"] not in ("", "FAIL_CLOSED")),
        "recovered_by_rule": sum(1 for r in rows if r["would_be_kept_by_record_keeping"]),
        "must_keep_the_carrier_answer": sum(1 for r in rows if r["must_keep_the_carrier_answer"]),
        "seconds": round(time.time() - started, 1),
        "rows": rows,
    }
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
