#!/usr/bin/env python3
"""Independent verifier for Project Brain typed evidence decisions.

This module does not import the producer. It recomputes the decision contract
from the input and compares every decision-relevant derived value.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib


def _safe(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _weight(item):
    return float(item["confidence"]) * float(item.get("strength", 1.0))


def _recompute(problem):
    policy = problem.get("policy") or {}
    min_support = float(policy.get("minimum_support_ratio", 0.60))
    max_conflict = float(policy.get("maximum_conflict_ratio", 0.50))
    min_groups = int(policy.get("minimum_independent_support_groups", 1))
    min_margin = float(policy.get("minimum_net_margin", 0.10))
    alt_ids = [x["id"] for x in problem["alternatives"]]
    out = {}
    for aid in alt_ids:
        required = [c for c in problem.get("constraints", []) if c["alternative"] == aid and c.get("required", True)]
        violated = sorted(c["id"] for c in required if str(c["state"]).upper() == "VIOLATED")
        unknown = sorted(c["id"] for c in required if str(c["state"]).upper() == "UNKNOWN")
        cstate = "DISQUALIFIED" if violated else "UNRESOLVED" if unknown else "ADMISSIBLE"
        supports = {}
        contradicts = {}
        ids = set()
        for item in problem.get("evidence", []):
            if item["alternative"] != aid:
                continue
            ids.add(item["id"])
            group = item["independence_group"]
            dest = supports if str(item["relation"]).upper() == "SUPPORTS" else contradicts
            dest[group] = max(dest.get(group, 0.0), _weight(item))
        support = sum(supports.values())
        contradiction = sum(contradicts.values())
        total = support + contradiction
        ratio = support / total if total else 0.0
        conflict = 2.0 * min(support, contradiction) / total if total else 0.0
        eligible = (
            cstate == "ADMISSIBLE" and total > 0 and len(supports) >= min_groups
            and ratio >= min_support and conflict <= max_conflict
        )
        out[aid] = {
            "alternative": aid,
            "constraint_state": cstate,
            "violated_constraints": violated,
            "unknown_constraints": unknown,
            "support_score": support,
            "contradiction_score": contradiction,
            "net_score": support - contradiction,
            "support_ratio": ratio,
            "conflict_ratio": conflict,
            "independent_support_groups": sorted(supports),
            "independent_contradiction_groups": sorted(contradicts),
            "contributing_evidence": sorted(ids),
            "eligible": eligible,
        }
    admissible = [x for x in out.values() if x["constraint_state"] == "ADMISSIBLE"]
    unresolved = [x for x in out.values() if x["constraint_state"] == "UNRESOLVED"]
    eligible = [x for x in out.values() if x["eligible"]]
    eligible.sort(key=lambda x: (-x["net_score"], -x["support_ratio"], x["alternative"]))
    if not admissible:
        status = "INSUFFICIENT" if unresolved else "NO_ADMISSIBLE_ALTERNATIVE"
        selected = None
    elif not eligible:
        status = "CONFLICTED" if any(x["conflict_ratio"] > max_conflict for x in admissible) else "INSUFFICIENT"
        selected = None
    elif len(eligible) == 1:
        status = "DECIDED"; selected = eligible[0]["alternative"]
    else:
        margin = eligible[0]["net_score"] - eligible[1]["net_score"]
        if margin < min_margin:
            status = "CONFLICTED"; selected = None
        else:
            status = "DECIDED"; selected = eligible[0]["alternative"]
    return out, status, selected


def verify(problem, result):
    if result.get("schema") != "PROJECT_BRAIN_TYPED_DECISION_RESULT_V1":
        return False, "RESULT_SCHEMA_INVALID"
    if result.get("input_sha256") != _canonical_hash(problem):
        return False, "INPUT_HASH_MISMATCH"
    recomputed, status, selected = _recompute(problem)
    if result.get("status") != status:
        return False, "STATUS_MISMATCH"
    if result.get("selected_alternative") != selected:
        return False, "SELECTED_ALTERNATIVE_MISMATCH"
    if result.get("model_dependency_count") != 0:
        return False, "MODEL_DEPENDENCY_NONZERO"
    by_result = {x["alternative"]: x for x in result.get("rankings") or []}
    if set(by_result) != set(recomputed):
        return False, "RANKING_ALTERNATIVE_SET_MISMATCH"
    exact_fields = [
        "constraint_state", "violated_constraints", "unknown_constraints",
        "independent_support_groups", "independent_contradiction_groups",
        "contributing_evidence", "eligible",
    ]
    numeric_fields = ["support_score", "contradiction_score", "net_score", "support_ratio", "conflict_ratio"]
    for aid, expected in recomputed.items():
        observed = by_result[aid]
        for field in exact_fields:
            if observed.get(field) != expected[field]:
                return False, f"FIELD_MISMATCH:{aid}:{field}"
        for field in numeric_fields:
            if not math.isclose(float(observed.get(field)), float(expected[field]), rel_tol=1e-12, abs_tol=1e-12):
                return False, f"NUMERIC_FIELD_MISMATCH:{aid}:{field}"
    if not isinstance(result.get("trace"), list) or len(result["trace"]) < 4:
        return False, "TRACE_INCOMPLETE"
    return True, "VERIFIED"


def run(args, root):
    input_path = _safe(root, args.get("input_path"))
    result_path = _safe(root, args.get("result_path"))
    if not input_path.is_file() or not result_path.is_file():
        raise RuntimeError("DECISION_VERIFIER_INPUT_MISSING")
    problem = json.loads(input_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    verified, reason = verify(problem, result)
    return {
        "adapter": "evidence_decision_verify",
        "verified": bool(verified),
        "reason": reason,
        "decision_id": result.get("decision_id"),
        "status": result.get("status"),
        "selected_alternative": result.get("selected_alternative"),
        "producer_independent": True,
        "model_dependency_count": 0,
    }
