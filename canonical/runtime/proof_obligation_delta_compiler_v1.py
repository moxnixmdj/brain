"""Executable proof-obligation normal form and exact residual delta compiler.

Zero-credit preproof compiler. It never infers semantics from names or prose.
A target obligation is discharged only by explicit, independently verified,
content-addressed bindings for scope components, atoms, invariants, and metrics.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_PROOF_OBLIGATION_DELTA_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_PROOF_OBLIGATION_DELTA_VERDICT_V1"
HEX = set("0123456789abcdef")


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "scope_relation": None,
        "residual": None,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def _sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and set(v.lower()) <= HEX


def _provenanced_components(raw: Any, label: str) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(raw, list) or not raw:
        return {}, [f"{label}_COMPONENTS_INVALID"]
    out: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(raw):
        if not isinstance(row, Mapping):
            errors.append(f"{label}_COMPONENT_NOT_OBJECT:{i}")
            continue
        cid = row.get("id")
        path = row.get("source_path")
        sha = row.get("source_sha")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{label}_COMPONENT_ID_INVALID:{i}")
            continue
        if cid in out:
            errors.append(f"{label}_COMPONENT_DUPLICATE:{cid}")
            continue
        if not isinstance(path, str) or not path or not _sha(sha):
            errors.append(f"{label}_COMPONENT_PROVENANCE_INVALID:{cid}")
            continue
        out[cid] = row
    return out, errors


def _string_set(raw: Any, label: str) -> tuple[set[str], list[str]]:
    if not isinstance(raw, list) or any(not isinstance(x, str) or not x for x in raw):
        return set(), [f"{label}_INVALID"]
    if len(raw) != len(set(raw)):
        return set(), [f"{label}_DUPLICATE"]
    return set(raw), []


def _receipt_ref(v: Any) -> bool:
    """A binding receipt must be an exact content-addressed canonical object."""
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v.get("path"))
        and _sha(v.get("git_blob_sha"))
    )


def _verified_bindings(raw: Any, kind: str) -> tuple[list[Mapping[str, Any]], list[str]]:
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], [f"{kind}_BINDINGS_INVALID"]
    errors: list[str] = []
    rows: list[Mapping[str, Any]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, Mapping):
            errors.append(f"{kind}_BINDING_NOT_OBJECT:{i}")
            continue
        if row.get("verified") is not True or row.get("independent") is not True:
            errors.append(f"{kind}_BINDING_NOT_INDEPENDENTLY_VERIFIED:{i}")
            continue
        if not _receipt_ref(row.get("receipt")):
            errors.append(f"{kind}_BINDING_RECEIPT_NOT_CONTENT_ADDRESSED:{i}")
            continue
        rows.append(row)
    return rows, errors


def _finite(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    return x if isfinite(x) else None


def compile_delta(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
        return _fail("SCHEMA_INVALID")

    target = doc.get("target")
    witness = doc.get("witness")
    if not isinstance(target, Mapping) or not isinstance(witness, Mapping):
        return _fail("TARGET_AND_WITNESS_REQUIRED")

    errors: list[str] = []
    t_scope, e = _provenanced_components(target.get("scope_components"), "TARGET")
    errors += e
    w_scope, e = _provenanced_components(witness.get("scope_components"), "WITNESS")
    errors += e

    t_atoms, e = _string_set(target.get("required_atoms", []), "TARGET_ATOMS")
    errors += e
    w_atoms, e = _string_set(witness.get("proved_atoms", []), "WITNESS_ATOMS")
    errors += e
    t_invariants, e = _string_set(target.get("required_invariants", []), "TARGET_INVARIANTS")
    errors += e
    w_invariants, e = _string_set(witness.get("proved_invariants", []), "WITNESS_INVARIANTS")
    errors += e

    scope_bindings, e = _verified_bindings(doc.get("scope_bindings"), "SCOPE")
    errors += e
    atom_bindings, e = _verified_bindings(doc.get("atom_bindings"), "ATOM")
    errors += e
    invariant_bindings, e = _verified_bindings(doc.get("invariant_bindings"), "INVARIANT")
    errors += e
    metric_bindings, e = _verified_bindings(doc.get("metric_bindings"), "METRIC")
    errors += e

    metrics = target.get("metric_requirements", [])
    if not isinstance(metrics, list):
        errors.append("TARGET_METRICS_INVALID")
        metrics = []
    metric_ids: set[str] = set()
    normalized_metrics: list[dict[str, Any]] = []
    for i, row in enumerate(metrics):
        if not isinstance(row, Mapping):
            errors.append(f"TARGET_METRIC_NOT_OBJECT:{i}")
            continue
        mid = row.get("metric")
        direction = row.get("direction")
        threshold = _finite(row.get("threshold"))
        if not isinstance(mid, str) or not mid or direction not in {"higher", "lower"} or threshold is None:
            errors.append(f"TARGET_METRIC_INVALID:{i}")
            continue
        if mid in metric_ids:
            errors.append(f"TARGET_METRIC_DUPLICATE:{mid}")
            continue
        metric_ids.add(mid)
        normalized_metrics.append({"metric": mid, "direction": direction, "threshold": threshold})

    bounds = witness.get("metric_bounds", {})
    if not isinstance(bounds, Mapping):
        errors.append("WITNESS_METRIC_BOUNDS_INVALID")
        bounds = {}

    if errors:
        return _fail(*errors)

    covered_scope: set[str] = set()
    scope_used: list[str] = []
    for row in scope_bindings:
        wc = row.get("witness_component")
        tc = row.get("target_component")
        relation = row.get("relation")
        if wc not in w_scope or tc not in t_scope or relation not in {"EXACT", "COVERS"}:
            return _fail("SCOPE_BINDING_ENDPOINT_OR_RELATION_INVALID")
        if tc in covered_scope:
            return _fail("TARGET_SCOPE_COMPONENT_MULTIPLY_BOUND:" + str(tc))
        covered_scope.add(str(tc))
        scope_used.append(str(row["receipt"]["path"]) + "@" + str(row["receipt"]["git_blob_sha"]))
    missing_scope = sorted(set(t_scope) - covered_scope)
    exact_scope = (
        not missing_scope
        and len(t_scope) == len(w_scope)
        and len(scope_bindings) == len(t_scope)
        and all(x.get("relation") == "EXACT" for x in scope_bindings)
    )
    scope_relation = None if missing_scope else ("EXACT" if exact_scope else "PROVEN_STRONGER")

    covered_atoms: set[str] = set()
    atom_used: list[str] = []
    for row in atom_bindings:
        wa, ta = row.get("witness_atom"), row.get("target_atom")
        if wa not in w_atoms or ta not in t_atoms:
            return _fail("ATOM_BINDING_ENDPOINT_INVALID")
        if ta in covered_atoms:
            return _fail("TARGET_ATOM_MULTIPLY_BOUND:" + str(ta))
        covered_atoms.add(str(ta))
        atom_used.append(str(row["receipt"]["path"]) + "@" + str(row["receipt"]["git_blob_sha"]))
    missing_atoms = sorted(t_atoms - covered_atoms)

    covered_invariants: set[str] = set()
    invariant_used: list[str] = []
    for row in invariant_bindings:
        wi, ti = row.get("witness_invariant"), row.get("target_invariant")
        if wi not in w_invariants or ti not in t_invariants:
            return _fail("INVARIANT_BINDING_ENDPOINT_INVALID")
        if ti in covered_invariants:
            return _fail("TARGET_INVARIANT_MULTIPLY_BOUND:" + str(ti))
        covered_invariants.add(str(ti))
        invariant_used.append(str(row["receipt"]["path"]) + "@" + str(row["receipt"]["git_blob_sha"]))
    missing_invariants = sorted(t_invariants - covered_invariants)

    metric_map: dict[str, Mapping[str, Any]] = {}
    metric_used: list[str] = []
    for row in metric_bindings:
        wm, tm = row.get("witness_metric"), row.get("target_metric")
        if not isinstance(wm, str) or tm not in metric_ids or wm not in bounds:
            return _fail("METRIC_BINDING_ENDPOINT_INVALID")
        if tm in metric_map:
            return _fail("TARGET_METRIC_BOUND_MULTIPLY_BOUND:" + str(tm))
        metric_map[str(tm)] = {"witness_metric": wm, "receipt": row["receipt"]}
        metric_used.append(str(row["receipt"]["path"]) + "@" + str(row["receipt"]["git_blob_sha"]))

    missing_metrics: list[str] = []
    failing_metrics: list[dict[str, Any]] = []
    passed_metrics: list[str] = []
    for req in normalized_metrics:
        mid = req["metric"]
        binding = metric_map.get(mid)
        if binding is None:
            missing_metrics.append(mid)
            continue
        bound = bounds.get(binding["witness_metric"])
        if not isinstance(bound, Mapping):
            return _fail("BOUND_INVALID:" + mid)
        key = "lower" if req["direction"] == "higher" else "upper"
        value = _finite(bound.get(key))
        passed = value is not None and (
            value >= req["threshold"] if req["direction"] == "higher" else value <= req["threshold"]
        )
        if passed:
            passed_metrics.append(mid)
        else:
            failing_metrics.append({
                "metric": mid,
                "direction": req["direction"],
                "threshold": req["threshold"],
                "bound_kind": key,
                "bound": value,
            })

    closed = not (missing_scope or missing_atoms or missing_invariants or missing_metrics or failing_metrics)
    residual = {
        "missing_scope_components": missing_scope,
        "missing_atoms": missing_atoms,
        "missing_invariants": missing_invariants,
        "missing_metric_bindings": sorted(missing_metrics),
        "failing_metric_bounds": failing_metrics,
    }
    return {
        "schema": VERDICT_SCHEMA,
        "status": "CLOSED_BY_EXPLICIT_VERIFIED_BINDINGS" if closed else "RESIDUAL_DELTA_OPEN",
        "pass": closed,
        "errors": [],
        "scope_relation": scope_relation,
        "covered": {
            "scope_components": sorted(covered_scope),
            "atoms": sorted(covered_atoms),
            "invariants": sorted(covered_invariants),
            "metrics": sorted(passed_metrics),
        },
        "residual": residual,
        "binding_receipts_used": sorted(set(scope_used + atom_used + invariant_used + metric_used)),
        "rule": "NO_BINDING_BY_NAME_PROSE_OR_FAMILY_ANALOGY__ONLY_INDEPENDENT_CONTENT_ADDRESSED_EXPLICIT_BINDINGS_DISCHARGE_TARGET_OBLIGATIONS",
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
