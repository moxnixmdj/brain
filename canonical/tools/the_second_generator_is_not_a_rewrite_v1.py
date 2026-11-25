"""One row, two candidate generators, one judge: take the union.

The session's strongest measured result was not new invention: two engines on two
branches each verify rows the other cannot, and together they reach **17/41 = 41.5%**
against 10/41 and 11/41 separately (overlap: 4 rows). They are complementary because
they read DIFFERENT evidence at the same fault site:

  - `the_relation_is_read_from_the_failing_run_v1` reads runtime values and the source
    text's own literals (anchors, split sides, guard conjuncts, raises predicates).
  - `the_demand_is_learned_from_the_run_v1` probes every boolean guard's value as
    type-level features and names a repair by which feature SEPARATES failing pytest
    nodes from passing ones.

Reimplementing the second inside the first's relation DSL would duplicate an instrument
and create a second place for the two-entry-path bug this build has already made twice.
So this driver runs BOTH over the same row and accepts a row if either verifies it.

Precedence is deliberate and cheap: the guard-probe engine is tried first because when
it works it usually works on its first candidate (measured: 3/4 rows at 29.3 s total),
and the relation engine second. A row verified by either is verified; the receipt always
says which engine produced the edit, so the union can never be mistaken for one engine's
work.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

DEMAND = "the_demand_is_learned_from_the_run_v1"
RELATION = "the_relation_is_read_from_the_failing_run_v1"


def _load(name: str):
    import importlib
    return importlib.import_module(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commits", default="canonical/corpus/single_line_fix_commits_20261123_V1.json")
    parser.add_argument("--receipt", default="/tmp/rel/union.json")
    parser.add_argument("--repos-root", default="/tmp/repos")
    parser.add_argument("--only", default="")
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--order", default="demand,relation")
    args = parser.parse_args()

    entries = json.loads(pathlib.Path(args.commits).read_text())["tasks"]
    if args.only:
        wanted = [p.strip().lower() for p in args.only.split(",") if p.strip()]
        entries = [e for e in entries if any(e["commit"].lower().startswith(p) for p in wanted)]

    demand = _load(DEMAND)
    rows: list[dict[str, Any]] = []
    started = time.time()
    for index, entry in enumerate(entries, 1):
        repo_path = pathlib.Path(args.repos_root) / entry["repo"]
        record: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"]}
        solved_by = None
        for engine_name in [n.strip() for n in args.order.split(",") if n.strip()]:
            if engine_name == "demand":
                try:
                    attempt = demand.explore(repo_path, entry, seconds=args.seconds)
                except Exception as error:
                    record.setdefault("errors", []).append(f"demand: {type(error).__name__}: {error}")
                    continue
                record["demand_stage"] = attempt.get("stage")
                if attempt.get("stage") == "VERIFIED":
                    solved_by = "demand"
                    record["demand_learned"] = attempt.get("learned")
                    break
            elif engine_name == "relation":
                # The relation engine is invoked as a subprocess because it owns its own
                # worktree, tracing and receipt shape; calling it in-process would make two
                # instruments share one interpreter's global state, which is exactly the
                # coupling that produced the project's earlier probe bugs.
                import subprocess
                target = pathlib.Path(args.receipt).with_suffix(f".relation.{entry['commit'][:8]}.json")
                subprocess.run([sys.executable, str(HERE / f"{RELATION}.py"),
                                "--commits", str(pathlib.Path(args.commits)),
                                "--receipt", str(target),
                                "--only", entry["commit"],
                                "--fresh"],
                               capture_output=True, text=True)
                if target.exists():
                    try:
                        inner = json.loads(target.read_text())["rows"][0]
                    except Exception:
                        inner = {}
                    record["relation_stage"] = inner.get("stage")
                    if inner.get("stage") == "VERIFIED":
                        solved_by = "relation"
                        record["relation_verified"] = inner.get("verified")
                        break
        record["solved_by"] = solved_by
        record["stage"] = "VERIFIED" if solved_by else record.get("demand_stage") or record.get("relation_stage") or "UNSOLVED"
        rows.append(record)
        print(f"  [{index}/{len(entries)}] {entry['repo']:<14} {entry['commit'][:8]} -> "
              f"{record['stage']}{' by ' + solved_by if solved_by else ''}")
        pathlib.Path(args.receipt).write_text(json.dumps(
            {"schema": "BRAIN_ONE_ROW_TWO_GENERATORS_V1", "rows": rows,
             "seconds": round(time.time() - started, 2)}, indent=2))

    verified = [r for r in rows if r["stage"] == "VERIFIED"]
    print(f"\n=== {len(verified)}/{len(rows)} verified, "
          f"{sum(1 for r in verified if r['solved_by'] == 'demand')} by the guard-probe engine, "
          f"{sum(1 for r in verified if r['solved_by'] == 'relation')} by the relation engine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
