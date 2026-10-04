from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence
import re

INPUT_SCHEMA = "PROJECT_BRAIN_THRESHOLD_PROOF_DAG_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_THRESHOLD_PROOF_DAG_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

METRIC_KINDS = {
    "ADDITIVE_THRESHOLD",
    "GATED_WEIGHTED_THRESHOLD",
    "RELATIVE_RATING_THRESHOLD",
    "MATCHED_NONINFERIORITY",
}

class ThresholdProofDagError(ValueError):
    pass

def _d(v: Any, field: str) -> Decimal:
    if isinstance(v, bool):
        raise ThresholdProofDagError(field + "_INVALID")
    try:
        x = Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ThresholdProofDagError(field + "_INVALID") from exc
    if not x.is_finite():
        raise ThresholdProofDagError(field + "_NONFINITE")
    return x

def _receipt(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v.get("path"))
        and isinstance(v.get("git_blob_sha"), str)
        and bool(HEX40.fullmatch(v["git_blob_sha"].lower()))
    )

def _positive_seconds(v: Any, field: str) -> Decimal:
    x = _d(v, field)
    if x <= 0:
        raise ThresholdProofDagError(field + "_MUST_BE_POSITIVE")
    return x

def _action_graph(actions: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    for i, raw in enumerate(actions):
        aid = raw.get("action_id")
        if not isinstance(aid, str) or not aid:
            raise ThresholdProofDagError(f"ACTION_ID_INVALID:{i}")
        if aid in by_id:
            raise ThresholdProofDagError("ACTION_ID_DUPLICATE:" + aid)
        by_id[aid] = raw

    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def dfs(aid: str) -> None:
        if aid in visited:
            return
        if aid in visiting:
            raise ThresholdProofDagError("ACTION_DEPENDENCY_CYCLE:" + aid)
        visiting.add(aid)
        deps = by_id[aid].get("depends_on", [])
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps):
            raise ThresholdProofDagError("ACTION_DEPENDENCIES_INVALID:" + aid)
        for dep in deps:
            if dep not in by_id:
                raise ThresholdProofDagError("ACTION_DEPENDENCY_UNKNOWN:" + aid + ":" + dep)
            dfs(dep)
        visiting.remove(aid)
        visited.add(aid)
        order.append(aid)

    for aid in by_id:
        dfs(aid)
    return by_id, order

def _closure(selected: set[str], by_id: Mapping[str, Mapping[str, Any]]) -> set[str]:
    out = set(selected)
    stack = list(selected)
    while stack:
        aid = stack.pop()
        for dep in by_id[aid].get("depends_on", []):
            if dep not in out:
                out.add(dep)
                stack.append(dep)
    return out

def _critical_path_seconds(selected: set[str], by_id: Mapping[str, Mapping[str, Any]], topo: Sequence[str]) -> Decimal:
    finish: dict[str, Decimal] = {}
    for aid in topo:
        if aid not in selected:
            continue
        deps = [d for d in by_id[aid].get("depends_on", []) if d in selected]
        start = max((finish[d] for d in deps), default=Decimal("0"))
        finish[aid] = start + _positive_seconds(by_id[aid].get("critical_path_seconds"), "CRITICAL_PATH_SECONDS")
    return max(finish.values(), default=Decimal("0"))

def _objective_tuple(selected: set[str], by_id: Mapping[str, Mapping[str, Any]], topo: Sequence[str]) -> tuple:
    cp = _critical_path_seconds(selected, by_id, topo)
    total = sum((_positive_seconds(by_id[a].get("critical_path_seconds"), "CRITICAL_PATH_SECONDS") for a in selected), Decimal("0"))
    return (cp, len(selected), total, tuple(sorted(selected)))

def _admissible_actions(doc: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], list[str], list[str]]:
    actions = doc.get("actions", [])
    if not isinstance(actions, list):
        raise ThresholdProofDagError("ACTIONS_INVALID")
    by_id, topo = _action_graph(actions)
    allow_fresh = doc.get("allow_fresh_reality", False)
    if not isinstance(allow_fresh, bool):
        raise ThresholdProofDagError("ALLOW_FRESH_REALITY_INVALID")
    blocked: list[str] = []
    active: dict[str, Mapping[str, Any]] = {}
    for aid, row in by_id.items():
        zr = row.get("zero_reality")
        if not isinstance(zr, bool):
            raise ThresholdProofDagError("ACTION_ZERO_REALITY_INVALID:" + aid)
        _positive_seconds(row.get("critical_path_seconds"), "CRITICAL_PATH_SECONDS")
        if not zr and not allow_fresh:
            blocked.append(aid)
        else:
            active[aid] = row

    changed = True
    while changed:
        changed = False
        blocked_set = set(blocked)
        for aid, row in list(active.items()):
            if aid in blocked_set:
                continue
            if any(dep in blocked_set or dep not in active for dep in row.get("depends_on", [])):
                blocked.append(aid)
                changed = True
        if changed:
            blocked_set = set(blocked)
            active = {k:v for k,v in active.items() if k not in blocked_set}
    return active, topo, sorted(set(blocked))

def _coverage_disjoint(selected: set[str], by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    seen: set[str] = set()
    for aid in selected:
        coverage = by_id[aid].get("coverage_ids", [])
        if not isinstance(coverage, list) or any(not isinstance(x, str) or not x for x in coverage):
            raise ThresholdProofDagError("ACTION_COVERAGE_INVALID:" + aid)
        for cid in coverage:
            if cid in seen:
                return False
            seen.add(cid)
    return True

def _gain(row: Mapping[str, Any], field: str) -> Decimal:
    x = _d(row.get(field, 0), field.upper())
    if x < 0:
        raise ThresholdProofDagError(field.upper() + "_NEGATIVE")
    return x

def _exact_min_cut(
    *,
    active: Mapping[str, Mapping[str, Any]],
    topo: Sequence[str],
    required: Decimal,
    gain_field: str,
    strict: bool = False,
) -> dict[str, Any] | None:
    if required <= 0 and not strict:
        return {"actions": [], "gain": "0", "critical_path_seconds": "0", "total_action_seconds": "0"}
    ids = list(active)
    if len(ids) > 24:
        return None

    best = None
    best_obj = None
    n = len(ids)
    for mask in range(1 << n):
        raw = {ids[i] for i in range(n) if mask & (1 << i)}
        selected = _closure(raw, active)
        if not selected.issubset(active.keys()):
            continue
        if raw != selected:
            continue
        if not _coverage_disjoint(selected, active):
            continue
        gain = sum((_gain(active[a], gain_field) for a in selected), Decimal("0"))
        enough = gain > required if strict else gain >= required
        if not enough:
            continue
        obj = _objective_tuple(selected, active, topo)
        if best_obj is None or obj < best_obj:
            best_obj = obj
            best = {
                "actions": sorted(selected),
                "gain": str(gain),
                "critical_path_seconds": str(obj[0]),
                "total_action_seconds": str(obj[2]),
            }
    return best

def _compile_additive(doc: Mapping[str, Any], target: Mapping[str, Any], active, topo) -> dict[str, Any]:
    total = _d(target.get("total_mass"), "TOTAL_MASS")
    threshold = _d(target.get("threshold_mass"), "THRESHOLD_MASS")
    lower = _d(target.get("current_lower_mass"), "CURRENT_LOWER_MASS")
    upper = _d(target.get("current_upper_mass"), "CURRENT_UPPER_MASS")
    if total <= 0 or not (Decimal("0") <= lower <= upper <= total) or not (Decimal("0") <= threshold <= total):
        raise ThresholdProofDagError("ADDITIVE_BOUNDS_INVALID")

    if lower >= threshold:
        return {"verdict":"PASS","lower":str(lower),"upper":str(upper),"threshold":str(threshold),"minimum_pass_cut":[]}
    if upper < threshold:
        return {"verdict":"FAIL","lower":str(lower),"upper":str(upper),"threshold":str(threshold),"minimum_fail_cut":[]}

    deficit = threshold - lower
    pass_cut = _exact_min_cut(active=active, topo=topo, required=deficit, gain_field="lower_gain_if_pass")
    fail_required = upper - threshold
    fail_cut = _exact_min_cut(active=active, topo=topo, required=fail_required, gain_field="upper_loss_if_fail", strict=True)
    return {
        "verdict":"OPEN",
        "lower":str(lower),
        "upper":str(upper),
        "threshold":str(threshold),
        "pass_deficit":str(deficit),
        "minimum_pass_cut":pass_cut,
        "minimum_fail_cut":fail_cut,
    }

def _compile_gated(doc: Mapping[str, Any], target: Mapping[str, Any], active, topo) -> dict[str, Any]:
    components = target.get("components")
    if not isinstance(components, list) or not components:
        raise ThresholdProofDagError("GATED_COMPONENTS_REQUIRED")
    threshold = _d(target.get("threshold_mass"), "THRESHOLD_MASS")
    lower = Decimal("0")
    upper = Decimal("0")
    seen = set()
    for i, comp in enumerate(components):
        if not isinstance(comp, Mapping):
            raise ThresholdProofDagError(f"GATED_COMPONENT_INVALID:{i}")
        cid = comp.get("id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ThresholdProofDagError(f"GATED_COMPONENT_ID_INVALID:{i}")
        seen.add(cid)
        weight = _d(comp.get("weight"), "COMPONENT_WEIGHT")
        lo = _d(comp.get("score_lower"), "COMPONENT_SCORE_LOWER")
        hi = _d(comp.get("score_upper"), "COMPONENT_SCORE_UPPER")
        if weight < 0 or not (Decimal("0") <= lo <= hi <= Decimal("1")):
            raise ThresholdProofDagError("GATED_COMPONENT_BOUNDS_INVALID:" + cid)
        gate = comp.get("gate")
        if gate not in {"PASS","FAIL","UNKNOWN"}:
            raise ThresholdProofDagError("GATED_COMPONENT_GATE_INVALID:" + cid)
        if gate == "PASS":
            lower += weight * lo
            upper += weight * hi
        elif gate == "UNKNOWN":
            upper += weight * hi

    shadow = dict(target)
    shadow["total_mass"] = str(sum((_d(c.get("weight"), "COMPONENT_WEIGHT") for c in components), Decimal("0")))
    shadow["current_lower_mass"] = str(lower)
    shadow["current_upper_mass"] = str(upper)
    return _compile_additive(doc, shadow, active, topo) | {"gated": True}

def _compile_relative(doc: Mapping[str, Any], target: Mapping[str, Any], active, topo) -> dict[str, Any]:
    threshold = _d(target.get("threshold_rating"), "THRESHOLD_RATING")
    lower = target.get("verified_rating_lower")
    bridge = target.get("verified_relative_bridge_receipt")
    if lower is not None:
        if not _receipt(bridge):
            raise ThresholdProofDagError("RELATIVE_RATING_BRIDGE_RECEIPT_REQUIRED")
        lo = _d(lower, "VERIFIED_RATING_LOWER")
        if lo >= threshold:
            return {"verdict":"PASS","verified_rating_lower":str(lo),"threshold_rating":str(threshold),"minimum_pass_cut":[]}
    eligible = []
    for aid,row in active.items():
        route = row.get("route_class")
        if route in {"OWNER_SCORE_RECEIPT","VERIFIED_RELATIVE_SCORE_BRIDGE"}:
            eligible.append(aid)
    if not eligible:
        return {"verdict":"OPEN","threshold_rating":str(threshold),"minimum_pass_cut":None,"reason":"NO_ADMISSIBLE_RELATIVE_SCORE_ROUTE"}
    best = None
    best_obj = None
    for aid in eligible:
        selected = _closure({aid}, active)
        if not _coverage_disjoint(selected, active):
            continue
        obj = _objective_tuple(selected, active, topo)
        if best_obj is None or obj < best_obj:
            best_obj = obj
            best = {"actions":sorted(selected),"critical_path_seconds":str(obj[0]),"total_action_seconds":str(obj[2])}
    return {"verdict":"OPEN","threshold_rating":str(threshold),"minimum_pass_cut":best,"reason":"RELATIVE_METRIC_REQUIRES_SCORE_OR_VERIFIED_RELATIVE_BRIDGE"}

def _compile_matched(doc: Mapping[str, Any], target: Mapping[str, Any], active, topo) -> dict[str, Any]:
    brain_lower = _d(target.get("brain_lower"), "BRAIN_LOWER")
    comparator_upper = _d(target.get("comparator_upper"), "COMPARATOR_UPPER")
    if brain_lower >= comparator_upper:
        return {"verdict":"PASS","brain_lower":str(brain_lower),"comparator_upper":str(comparator_upper),"minimum_pass_cut":[]}
    gap = comparator_upper - brain_lower
    cut = _exact_min_cut(active=active, topo=topo, required=gap, gain_field="margin_gain_if_pass")
    return {"verdict":"OPEN","brain_lower":str(brain_lower),"comparator_upper":str(comparator_upper),"margin_gap":str(gap),"minimum_pass_cut":cut}

def compile_threshold_proof_dag(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise ThresholdProofDagError("SCHEMA_INVALID")
        target = doc.get("target")
        if not isinstance(target, Mapping):
            raise ThresholdProofDagError("TARGET_REQUIRED")
        target_id = target.get("id")
        if not isinstance(target_id, str) or not target_id:
            raise ThresholdProofDagError("TARGET_ID_REQUIRED")
        if not _receipt(target.get("receipt")):
            raise ThresholdProofDagError("TARGET_RECEIPT_NOT_CONTENT_ADDRESSED")
        metric_kind = target.get("metric_kind")
        if metric_kind not in METRIC_KINDS:
            raise ThresholdProofDagError("METRIC_KIND_INVALID")

        active, topo, blocked = _admissible_actions(doc)

        if metric_kind == "ADDITIVE_THRESHOLD":
            compiled = _compile_additive(doc, target, active, topo)
        elif metric_kind == "GATED_WEIGHTED_THRESHOLD":
            compiled = _compile_gated(doc, target, active, topo)
        elif metric_kind == "RELATIVE_RATING_THRESHOLD":
            compiled = _compile_relative(doc, target, active, topo)
        else:
            compiled = _compile_matched(doc, target, active, topo)

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS" if compiled.get("verdict") in {"PASS","FAIL","OPEN"} else "FAIL_CLOSED",
            "target_id": target_id,
            "metric_kind": metric_kind,
            "compiled": compiled,
            "blocked_fresh_reality_actions": blocked,
            "rules": [
                "OUTPUT_ONLY__DO_NOT_REQUIRE_FULL_BENCHMARK_WHEN_A_SOUND_THRESHOLD_CERTIFICATE_ALREADY_SETTLES_THE_PREDICATE",
                "NO_SCORE_INHERITANCE_ACROSS_NON_EQUIVALENT_HARNESSES",
                "NO_RELATIVE_RATING_FROM_ABSOLUTE_PERFORMANCE_WITHOUT_VERIFIED_RELATIVE_SCORE_BRIDGE",
                "NO_DOUBLE_COUNTING_OVERLAPPING_COVERAGE",
                "FRESH_REALITY_ACTIONS_REQUIRE_EXPLICIT_AUTHORITY",
                "PLANNER_OUTPUT_GRANTS_ZERO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_CREDIT",
            ],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except ThresholdProofDagError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
