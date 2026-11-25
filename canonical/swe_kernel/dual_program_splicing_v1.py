#!/usr/bin/env python3
"""Splice two partial repairs and verify the union of their counterexamples.

No model, no corpus of answers, no stored parameters. The two programs are
candidate patches proposed by the project's own miners; the only authority is
the project's own pytest runner on the tests each candidate cannot pass alone.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
for entry in (str(ROOT), str(ROOT / "canonical" / "tools"),
              str(ROOT / "canonical" / "swe_kernel")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_DUAL_PROGRAM_SPLICING_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "S1": "two candidates that pass disjoint test partitions can be spliced into one that passes their union",
    "S2": "a splice is accepted only after the project's own runner verifies the full union",
    "S3": "no commit diff, model, network or stored parameter is read",
}
MAX_SPLICES = 32


def edits(parent: str, candidate: str) -> list[dict[str, Any]]:
    """Line-level edit blocks from `parent` to `candidate`."""
    before = parent.splitlines(keepends=True)
    after = candidate.splitlines(keepends=True)
    out: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before, after).get_opcodes():
        if tag != "equal":
            out.append({"tag": tag, "i1": i1, "i2": i2, "j1": j1, "j2": j2,
                        "old": before[i1:i2], "new": after[j1:j2]})
    return out


def splice(parent: str, candidate_a: str, candidate_b: str) -> list[str]:
    """Combine non-overlapping edits of A and B; for overlaps try either side."""
    before = parent.splitlines(keepends=True)
    a_edits = edits(parent, candidate_a)
    b_edits = edits(parent, candidate_b)
    out: list[str] = []

    def render(blocks: Sequence[dict[str, Any]]) -> str | None:
        ordered = sorted(blocks, key=lambda block: (block["i1"], block["i2"]))
        cursor = 0
        pieces: list[str] = []
        for block in ordered:
            if block["i1"] < cursor:
                return None
            pieces.extend(before[cursor:block["i1"]])
            pieces.extend(block["new"])
            cursor = block["i2"]
        pieces.extend(before[cursor:])
        return "".join(pieces)

    def remember(text: str | None) -> None:
        if text is not None and text != parent and text not in out:
            out.append(text)

    # Plain union, plus each side alone in case the union conflicts.
    remember(render([*a_edits, *b_edits]))
    remember(render(a_edits))
    remember(render(b_edits))
    for a in a_edits:
        for b in b_edits:
            overlap = a["i1"] < b["i2"] and b["i1"] < a["i2"]
            if not overlap:
                continue
            remember(render([a, *[other for other in b_edits if other is not b]]))
            remember(render([b, *[other for other in a_edits if other is not a]]))
    return out[:MAX_SPLICES]


def run_nodes(worktree: pathlib.Path, test_rel: str, nodes: Sequence[str],
              seconds: int) -> dict[str, str]:
    if not nodes:
        return {}
    command = [sys.executable, "-m", "pytest", *nodes, "-q", "--tb=no",
               "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=seconds,
                              env={**os.environ, **identify.fresh_bytecode(worktree)})
    except subprocess.TimeoutExpired:
        return {node: "TIMEOUT" for node in nodes}
    text = done.stdout + done.stderr
    verdicts: dict[str, str] = {}
    for line in text.splitlines():
        for node in nodes:
            if node in line and line.strip().startswith(("PASSED", "FAILED")):
                verdicts[node] = "PASS" if line.strip().startswith("PASSED") else "FAIL"
    if not verdicts:
        verdicts = {node: ("PASS" if done.returncode == 0 else "FAIL") for node in nodes}
    return verdicts


def splice_and_verify(worktree: pathlib.Path, source_rel: str, test_rel: str,
                      parent_source: str, candidate_a: str, candidate_b: str,
                      partition_a: Sequence[str], partition_b: Sequence[str],
                      seconds: int = 20) -> dict[str, Any]:
    source_file = worktree / source_rel
    union = list(dict.fromkeys([*partition_a, *partition_b]))
    verdicts: dict[str, Any] = {"partition_a": partition_a, "partition_b": partition_b,
                                "union": union, "splices_tested": 0, "verification": None}
    try:
        source_file.write_text(parent_source, encoding="utf-8")
        verdicts["a_on_partition_a"] = run_nodes(worktree, test_rel, partition_a, seconds)
        verdicts["b_on_partition_b"] = run_nodes(worktree, test_rel, partition_b, seconds)
        candidates = splice(parent_source, candidate_a, candidate_b)
        verdicts["splices_generated"] = len(candidates)
        for candidate in candidates:
            verdicts["splices_tested"] += 1
            source_file.write_text(candidate, encoding="utf-8")
            outcome = run_nodes(worktree, test_rel, union, seconds)
            if outcome and all(value == "PASS" for value in outcome.values()):
                verdicts["verification"] = {
                    "source": candidate, "outcome": outcome,
                    "from_a_edits": len(edits(parent_source, candidate_a)),
                    "from_b_edits": len(edits(parent_source, candidate_b)),
                }
                break
    finally:
        source_file.write_text(parent_source, encoding="utf-8")
    verdicts["verified"] = verdicts["verification"] is not None
    return verdicts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--candidate-a", required=True)
    parser.add_argument("--candidate-b", required=True)
    parser.add_argument("--partition-a", nargs="+", default=[])
    parser.add_argument("--partition-b", nargs="+", default=[])
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args(argv)
    worktree = pathlib.Path(args.worktree)
    started = time.time()
    result = splice_and_verify(
        worktree, args.source, args.test,
        (worktree / args.source).read_text(encoding="utf-8"),
        pathlib.Path(args.candidate_a).read_text(encoding="utf-8"),
        pathlib.Path(args.candidate_b).read_text(encoding="utf-8"),
        args.partition_a, args.partition_b, args.seconds,
    )
    report = {"schema": SCHEMA, "authority": AUTHORITY,
              "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "declared_before_the_run": DECLARED, **result,
              "seconds": round(time.time() - started, 1),
              "model_calls": 0, "network_calls": 0, "parameters_stored": 0}
    pathlib.Path(args.receipt).write_text(json.dumps(report, indent=2, sort_keys=True),
                                          encoding="utf-8")
    print(json.dumps({"verified": report["verified"],
                      "splices_tested": report["splices_tested"]}, indent=2))
    return 0 if report["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
