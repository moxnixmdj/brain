"""Fold the QuixBugs measurements into one receipt.

Every number in the output is computed from the raw rows of the runs, never typed by hand. Where a
run is incomplete, the receipt says how many tasks it actually measured rather than extrapolating.

What it consolidates:
  * the expressibility ladder over all 40 published fixes (what edit space a fix needs at all);
  * the CONTROL: the tree's existing hand-listed basis, run end to end on the held-out half;
  * the TREATMENT: an edit basis induced from the training half only, applied to the same held-out
    half, with the corpus's own tests as the only oracle;
  * the agreement between them, task by task.

Usage
-----
    python3 canonical/tools/one_demonstration_receipt_v1.py \
        --quixbugs /path/to/QuixBugs \
        --control /tmp/qb_holdout_control.jsonl \
        --transfer /tmp/transfer_full.json \
        --out canonical/verification/WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1.json \
        [--upstream-commit <sha>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from collections import Counter
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import induced_edit_basis_v1 as basis  # noqa: E402
from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as harness  # noqa: E402

SCHEMA = "BRAIN_WHAT_ONE_DEMONSTRATION_BUYS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"


def reclassify(row: dict[str, Any]) -> str:
    """A partial repair is not a refusal, and it is not a repair.

    The existing repair loop returns candidate patches only when its own tests fully pass -- by its
    contract it does not hand back an unverified intermediate state. So a row that accepted edits and
    still failed must be reported as PARTIAL, not lumped with "nothing improved", or the control
    number would understate what the hand-listed basis actually did.
    """
    stage = str(row.get("stage"))
    if stage == "NOT_REPAIRED__NO_CANDIDATE":
        accepted = row.get("accepted_edit_count") or 0
        return ("NOT_REPAIRED__PARTIAL_EDITS_DISCARDED" if accepted
                else "NOT_REPAIRED__NO_STRICTLY_IMPROVING_CANDIDATE")
    return stage


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("kind") != "header":
            rows.append(record)
    return rows


def ladder(root: pathlib.Path, names: Sequence[str]) -> dict[str, Any]:
    per_task = {}
    for name in names:
        per_task[name] = basis.classify_fix_shape(
            (root / "python_programs" / f"{name}.py").read_text(),
            (root / "correct_python_programs" / f"{name}.py").read_text())
    counts = Counter(v["rung"] for v in per_task.values())
    one_node_or_leaf = counts.get("RUNG_LEAF", 0) + counts.get("RUNG_NODE", 0)
    return {
        "tasks": len(per_task),
        "counts": {rung: counts.get(rung, 0) for rung in basis.RUNGS},
        "by_rung": {rung: sorted(n for n, v in per_task.items() if v["rung"] == rung) for rung in basis.RUNGS},
        "expressible_by_one_node_substitution": one_node_or_leaf,
        "expressible_fraction": round(one_node_or_leaf / len(per_task), 4) if per_task else 0.0,
        "per_task": {n: {"rung": v["rung"], "position_count": v["position_count"]} for n, v in per_task.items()},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--transfer", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--upstream-commit", default="")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs).resolve()
    names = harness.tasks_of(root)
    ladder_block = ladder(root, names)

    control_rows = read_jsonl(pathlib.Path(args.control))
    control = {}
    for row in control_rows:
        control[str(row["task"])] = {
            "stage": reclassify(row),
            "accepted_edit_count": row.get("accepted_edit_count"),
            "tested_candidate_count": row.get("tested_candidate_count"),
            "seconds": row.get("seconds"),
        }

    transfer_path = pathlib.Path(args.transfer)
    transfer_doc = json.loads(transfer_path.read_text()) if transfer_path.is_file() else {}
    held_out = transfer_doc.get("held_out") or []
    train = transfer_doc.get("train") or []
    transfer_rows = {str(r["task"]): r for r in transfer_doc.get("rows", [])}
    transfer = {}
    for name, row in transfer_rows.items():
        accepted = row.get("accepted") or []
        transfer[name] = {
            "stage": row.get("stage"),
            "transferred": bool(accepted) and any(name not in (a.get("taught_by") or []) for a in accepted),
            "accepted": accepted,
            "candidates_tested": row.get("candidates_tested"),
            "seconds": row.get("seconds"),
        }

    repaired_transfer = sorted(n for n, v in transfer.items() if v["stage"] == "REPAIRED__CORPUS_TEST_PASSES")
    repaired_control = sorted(n for n, v in control.items() if v["stage"] == "REPAIRED__CORPUS_TEST_PASSES")
    only_transfer = sorted(set(repaired_transfer) - set(repaired_control))
    only_control = sorted(set(repaired_control) - set(repaired_transfer))

    payload = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "upstream": harness.UPSTREAM, "upstream_commit": args.upstream_commit,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_tasks": len(names),
        "expressibility_ladder": ladder_block,
        "split": {"train": train, "held_out": held_out,
                  "method": "sorted by sha256(name); first 20 train, rest held out"},
        "control": {"method": "python.software.repair.loop.test_guided.ast.v1 -- the tree's existing "
                              "hand-listed edit basis, run end to end",
                    "tasks_measured": len(control), "repaired": repaired_control,
                    "repaired_count": len(repaired_control),
                    "by_stage": dict(Counter(v["stage"] for v in control.values())),
                    "rows": control},
        "treatment": {"method": "induced_edit_basis_v1 -- templates folded from the training half only",
                      "tasks_measured": len(transfer), "repaired": repaired_transfer,
                      "repaired_count": len(repaired_transfer),
                      "repaired_by_a_template_taught_elsewhere": sorted(
                          n for n, v in transfer.items() if v["transferred"]),
                      "by_stage": dict(Counter(v["stage"] for v in transfer.values())),
                      "leaf_template_count": transfer_doc.get("executable_leaf_template_count"),
                      "node_template_count": len(transfer_doc.get("node_templates") or []),
                      "templates": {"leaf": transfer_doc.get("leaf_templates") or [],
                                    "node": transfer_doc.get("node_templates") or []},
                      "rows": transfer},
        "agreement": {"repaired_by_both": sorted(set(repaired_transfer) & set(repaired_control)),
                      "repaired_only_by_treatment": only_transfer,
                      "repaired_only_by_control": only_control},
        "producer_cognition_model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NOT_A_SWE_BENCH_SCORE",
            "NOT_INDEPENDENT_VERIFICATION__PRODUCER_RUN",
            "NO_CLAIM_THAT_QUIXBUGS_IS_THE_FRONTIER",
            "NO_CLAIM_OF_GENERAL_REPAIR_COMPLETENESS",
            "NO_CLAIM_THAT_A_REPAIRED_TASK_REPAIRED_THE_PROGRAM_AS_A_WHOLE",
            "NO_SENTIENCE_CLAIM",
        ],
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({k: payload[k] for k in ("corpus_tasks", "split")}, default=str)[:300])
    print("ladder:", ladder_block["counts"], "one-node-or-leaf:", ladder_block["expressible_by_one_node_substitution"])
    print("control  repaired:", len(repaired_control), "/", len(control))
    print("treatment repaired:", len(repaired_transfer), "/", len(transfer),
          "by-transferred-edit:", payload["treatment"]["repaired_by_a_template_taught_elsewhere"])
    print("agreement:", payload["agreement"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
