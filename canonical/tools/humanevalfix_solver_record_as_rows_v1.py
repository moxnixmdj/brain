#!/usr/bin/env python3
"""The committed record of the repair solver on the scored HumanEvalFix bugs, as the rows the stream reads.

The files a run writes are not in the tree. The committed record
(canonical/verification/HUMANEVALFIX_REPAIR_SOLVER_20261112_V1.json) keeps every bug as one short
list. This gives the rows back in the form canonical/tools/humanevalfix_experience_stream_measure_v1.py
takes as --solver-record, so the stream can be run again from the tree and the two public data files.

Nothing is measured here and nothing is guessed: a record whose key is not the one written below is
refused.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

KEY = "[repaired, right as far as checked, is the published fix, processes started, seconds, status, lines removed, lines put in]"
AT_THE_WALL = "STOPPED_AT_THE_WALL_LIMIT"
SCHEMA = "BRAIN_HUMANEVALFIX_REPAIR_SOLVER_RECORD_V1"


def rows(record: Mapping[str, Any]) -> dict[str, Any]:
    """The record as {"which", "timeout_s", "wall_limit_s", "per_bug": {name: row}}."""
    if record.get("schema") != SCHEMA:
        raise ValueError(f"not a record of the solver on HumanEvalFix: schema {record.get('schema')!r}")
    if record.get("per_bug_key") != KEY:
        raise ValueError("the record's rows are not in the order this reads; nothing is guessed")
    per_bug: dict[str, dict[str, Any]] = {}
    for name, row in record["per_bug"].items():
        if len(row) != 8:
            raise ValueError(f"{name}: {len(row)} fields where 8 are named")
        repaired, right, published, started, seconds, status, removed, put_in = row
        at_the_wall = status == AT_THE_WALL
        finished = status is not None and not at_the_wall
        if repaired and not finished:
            raise ValueError(f"{name}: repaired and not finished cannot both be")
        lines = None if removed is None or put_in is None else {"removed": list(removed), "put_in": list(put_in)}
        per_bug[name] = {"usable": True, "repaired": bool(repaired), "right_as_far_as_checked": bool(repaired and right),
                         "is_the_published_fix": bool(repaired and published), "processes_started": started, "seconds": seconds,
                         "status": None if at_the_wall else status, "finished": finished, "stopped_at_the_wall_limit": at_the_wall,
                         "lines": lines if repaired else None}
    run = record["run"]
    return {"from_the_committed_record": True, "which": run["which"], "timeout_s": run["timeout_s"], "wall_limit_s": run["wall_limit_s"],
            "nothing_taught": run.get("nothing_taught"), "per_bug": per_bug}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--record", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    out = rows(json.loads(args.record.read_text(encoding="utf-8")))
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    repaired = sum(1 for row in out["per_bug"].values() if row["repaired"])
    print(f"{len(out['per_bug'])} bugs, {repaired} repaired, {sum(1 for row in out['per_bug'].values() if row['finished'])} finished -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
