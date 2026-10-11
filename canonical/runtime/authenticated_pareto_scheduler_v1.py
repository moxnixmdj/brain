"""Receipt-bound capability/resource Pareto scheduler.

Caller-supplied utility fields are rejected unless the exact metrics are bound by
an independent measurement receipt.  Hard-$0 candidates only.  Promotion is not
performed here; this module only returns the authenticated nondominated set.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_PARETO_SCHEDULER_V1"
MAX_KEYS = ("capability_gain_lcb", "generalization_lcb", "reliability_lcb", "reuse_breadth_lcb", "success_probability_lcb")
MIN_KEYS = ("latency_ms_ucb", "compute_units_ucb", "memory_mb_ucb", "cost_usd_ucb")
ALL_KEYS = MAX_KEYS + MIN_KEYS


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _valid_sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason,
            "schedule_authority": False, "promotion_authority": False, "terminal_authority": False,
            "terminal_credit_delta": 0, "incremental_spend_usd": 0, **extra}


def _dominates(a: Mapping[str, float], b: Mapping[str, float]) -> bool:
    no_worse = all(a[k] >= b[k] for k in MAX_KEYS) and all(a[k] <= b[k] for k in MIN_KEYS)
    strictly = any(a[k] > b[k] for k in MAX_KEYS) or any(a[k] < b[k] for k in MIN_KEYS)
    return no_worse and strictly


def compile_schedule(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    ids = set()
    for c in candidates:
        if not isinstance(c, Mapping) or not isinstance(c.get("candidate_id"), str) or not c["candidate_id"]:
            return _fail("CANDIDATE_INVALID")
        if c["candidate_id"] in ids:
            return _fail("DUPLICATE_CANDIDATE_ID", candidate_id=c["candidate_id"])
        ids.add(c["candidate_id"])
        metrics = c.get("metrics")
        receipt = c.get("measurement_receipt")
        if not isinstance(metrics, Mapping) or any(k not in metrics or not isinstance(metrics[k], (int, float)) for k in ALL_KEYS):
            return _fail("METRICS_INCOMPLETE", candidate_id=c["candidate_id"])
        if not isinstance(receipt, Mapping) or receipt.get("independently_verified") is not True or not _valid_sha(receipt.get("sha256")):
            return _fail("MEASUREMENT_RECEIPT_INVALID", candidate_id=c["candidate_id"])
        subject = _sha({"candidate_id": c["candidate_id"], "metrics": {k: metrics[k] for k in ALL_KEYS}})
        if receipt.get("subject_sha256") != subject:
            return _fail("MEASUREMENT_RECEIPT_SUBJECT_MISMATCH", candidate_id=c["candidate_id"])
        if float(metrics["cost_usd_ucb"]) != 0.0:
            return _fail("HARD_ZERO_SPEND_VIOLATION", candidate_id=c["candidate_id"], cost_usd_ucb=metrics["cost_usd_ucb"])
        rows.append({"candidate_id": c["candidate_id"], "metrics": {k: float(metrics[k]) for k in ALL_KEYS},
                     "measurement_receipt_sha256": receipt["sha256"], "subject_sha256": subject})
    if not rows:
        return _fail("NO_CANDIDATES")

    nondominated = []
    dominated_by = {}
    for row in rows:
        dominators = [other["candidate_id"] for other in rows if other is not row and _dominates(other["metrics"], row["metrics"])]
        if dominators:
            dominated_by[row["candidate_id"]] = sorted(dominators)
        else:
            nondominated.append(row)
    nondominated.sort(key=lambda x: x["candidate_id"])
    core = {"nondominated_candidate_ids": [x["candidate_id"] for x in nondominated], "dominated_by": dominated_by,
            "measurement_subjects": {x["candidate_id"]: x["subject_sha256"] for x in rows}}
    return {"schema": SCHEMA, "pass": True, "status": "PASS__AUTHENTICATED_ZERO_SPEND_PARETO_FRONTIER_COMPILED",
            "reason": None, **core, "schedule_receipt_sha256": _sha(core), "schedule_authority": True,
            "promotion_authority": False, "terminal_authority": False, "terminal_credit_delta": 0,
            "incremental_spend_usd": 0}
