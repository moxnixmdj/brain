from __future__ import annotations
from itertools import combinations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CONTRACT_NATIVE_ACTUAL_POLICY_V1"

def _structured(task: Mapping[str, Any]) -> dict[str, Any]:
    reqs = task.get("requirements")
    if not isinstance(reqs, list):
        raise ValueError("REQUIREMENTS_REQUIRED")
    graph = []
    for row in reqs:
        if not isinstance(row, Mapping):
            raise ValueError("REQUIREMENT_INVALID")
        if row.get("required") is True:
            fid = row.get("id")
            coeff = row.get("coefficient")
            if not isinstance(fid, str) or not isinstance(coeff, int) or isinstance(coeff, bool):
                raise ValueError("REQUIREMENT_FIELDS_INVALID")
            graph.append({"factor": fid, "coefficient": coeff})
    graph.sort(key=lambda x: x["factor"])
    return {"graph": graph}

def _trajectory(task: Mapping[str, Any]) -> dict[str, Any]:
    traj = task.get("trajectory")
    repairs = task.get("repair_candidates")
    if not isinstance(traj, list) or not isinstance(repairs, list):
        raise ValueError("TRAJECTORY_OR_REPAIRS_REQUIRED")
    failed = [row for row in traj if isinstance(row, Mapping) and row.get("invariant_pass") is False]
    if not failed:
        raise ValueError("NO_CAUSAL_FAILURE_VISIBLE")
    cause = min(int(row["step"]) for row in failed)
    matches = [
        row for row in repairs
        if isinstance(row, Mapping) and row.get("targets_step") == cause and isinstance(row.get("id"), str)
    ]
    if len(matches) != 1:
        raise ValueError("REPAIR_NOT_UNIQUE")
    return {"cause_step": cause, "repair_id": matches[0]["id"], "evidence_steps": [cause]}

def _synthesis(task: Mapping[str, Any]) -> dict[str, Any]:
    rows = task.get("evidence")
    if not isinstance(rows, list):
        raise ValueError("EVIDENCE_REQUIRED")
    required, optional = [], []
    uncertainty = []
    provenance = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("EVIDENCE_ROW_INVALID")
        cid = row.get("claim_id")
        role = row.get("role")
        support = row.get("support")
        prov = row.get("provenance")
        if not isinstance(cid, str) or not isinstance(prov, list):
            raise ValueError("EVIDENCE_FIELDS_INVALID")
        if role == "required":
            required.append(cid)
        elif role == "optional":
            optional.append(cid)
        elif role != "forbidden":
            raise ValueError("ROLE_INVALID")
        if role in {"required", "optional"}:
            provenance[cid] = list(prov)
            if support == "conflicted":
                uncertainty.append(cid)
    selected = sorted(required) + sorted(optional)
    return {
        "selected_claims": selected,
        "uncertainty_claims": sorted(x for x in uncertainty if x in set(selected)),
        "claim_provenance": {cid: provenance[cid] for cid in selected},
    }

def _professional(task: Mapping[str, Any]) -> dict[str, Any]:
    weights = task.get("rubric_weights")
    acts = task.get("edit_candidates")
    budget = task.get("edit_budget")
    if not isinstance(weights, Mapping) or not isinstance(acts, list) or not isinstance(budget, int):
        raise ValueError("PROFESSIONAL_TASK_INVALID")
    best = None
    n = len(acts)
    for mask in range(1 << n):
        chosen = [acts[i] for i in range(n) if mask & (1 << i)]
        if any(not isinstance(a, Mapping) for a in chosen):
            raise ValueError("EDIT_INVALID")
        if any(a.get("supported") is not True or a.get("hard_violation") is True for a in chosen):
            continue
        cost = sum(int(a.get("cost")) for a in chosen)
        if cost > budget:
            continue
        score = 0
        for a in chosen:
            scores = a.get("scores")
            if not isinstance(scores, Mapping):
                raise ValueError("SCORES_INVALID")
            score += sum(int(weights[d]) * int(scores[d]) for d in weights)
        ids = tuple(sorted(str(a.get("id")) for a in chosen))
        key = (-score, cost, ids)
        if best is None or key < best[0]:
            best = (key, ids)
    if best is None:
        raise ValueError("NO_ADMISSIBLE_PLAN")
    return {"selected_edits": list(best[1])}

def solve(public_case: Mapping[str, Any]) -> dict[str, Any]:
    contract = public_case.get("contract")
    task = public_case.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("TASK_REQUIRED")
    if contract == "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        return _structured(task)
    if contract == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        return _trajectory(task)
    if contract == "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        return _synthesis(task)
    if contract == "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _professional(task)
    raise ValueError("UNKNOWN_CONTRACT")
