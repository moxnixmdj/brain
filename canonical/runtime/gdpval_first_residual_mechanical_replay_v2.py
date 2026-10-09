"""Replay current V1 and V2 against the frozen GDPval-220 first-residual corpus.

This measures verifier-route availability only.  It does not assert that a Brain
artifact satisfies the criterion and grants no benchmark, acceptance, or terminal
credit.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from canonical.runtime import gdpval_objective_artifact_criteria_v1 as v1
from canonical.runtime import gdpval_objective_artifact_criteria_v2 as v2

SCHEMA = "PROJECT_BRAIN_GDPVAL_FIRST_RESIDUAL_MECHANICAL_REPLAY_V2"
DEFAULT_EVIDENCE = Path("canonical/evidence/GDPVAL_PUBLIC_220_OBJECTIVE_ARTIFACT_CRITERIA_EXECUTION_20261007_V1.json")


def replay(path: str | Path = DEFAULT_EVIDENCE) -> dict[str, Any]:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = list(data.get("tasks") or [])
    if len(rows) != 220:
        raise ValueError("FROZEN_GDPVAL_TASK_COUNT_MISMATCH")

    baseline = []
    current = []
    newly = []
    unresolved = []
    relation_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()

    for row in rows:
        residual = row.get("first_unresolved_scored_criterion")
        if not isinstance(residual, dict):
            raise ValueError("FIRST_RESIDUAL_MISSING:" + str(row.get("row_idx")))
        criterion = residual.get("criterion")
        cid = residual.get("criterion_id")
        if not isinstance(criterion, str) or not criterion.strip():
            raise ValueError("FIRST_RESIDUAL_TEXT_INVALID:" + str(row.get("row_idx")))

        old = v1.compile_criterion(criterion, criterion_id=cid)
        new = v2.compile_criterion(criterion, criterion_id=cid)
        old_ok = old.get("status") == "COMPILED_OBJECTIVE_CHECK"
        new_ok = new.get("status") == "COMPILED_OBJECTIVE_CHECK"
        if old_ok:
            baseline.append(int(row["row_idx"]))
        if new_ok:
            current.append(int(row["row_idx"]))
            relation_counts[str(new.get("criterion_to_check_relation"))] += 1
            for check in new.get("checks") or []:
                kind_counts[str(check.get("kind"))] += 1
        else:
            unresolved.append(int(row["row_idx"]))
        if new_ok and not old_ok:
            newly.append({
                "row_idx": int(row["row_idx"]),
                "task_id": row.get("task_id"),
                "criterion_id": cid,
                "criterion_sha256": new.get("criterion_sha256"),
                "check_kinds": [x.get("kind") for x in new.get("checks") or []],
                "criterion_to_check_relation": new.get("criterion_to_check_relation"),
            })

    if not set(baseline).issubset(set(current)):
        raise AssertionError("V2_REGRESSED_V1_FIRST_RESIDUAL_COVERAGE")

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_V1_AND_V2_FIRST_RESIDUAL_ROUTE_AVAILABILITY_REPLAY",
        "source_path": str(source),
        "source_schema": data.get("schema"),
        "source_population_task_count": len(rows),
        "v1_first_residual_compilable_count": len(baseline),
        "v2_first_residual_compilable_count": len(current),
        "v2_new_first_residual_compilable_count": len(newly),
        "v2_unresolved_first_residual_count": len(unresolved),
        "v1_regression_count": 0,
        "newly_compilable": newly,
        "criterion_relation_counts": dict(sorted(relation_counts.items())),
        "check_kind_counts": dict(sorted(kind_counts.items())),
        "interpretation": (
            "A compilable first residual has a sound machine-verifier route available; "
            "it is not evidence that any candidate artifact passes that criterion. "
            "Advancing a task requires a verified artifact receipt, then recomputation "
            "of that task's next unresolved criterion."
        ),
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "terminal_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))
