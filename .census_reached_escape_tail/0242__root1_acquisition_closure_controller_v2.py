from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import structural_transfer_v3 as transfer

SCHEMA = "PROJECT_BRAIN_ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2"
COVERAGE_STATUSES = {"VERIFIED_OWNED", "VERIFIED_ACQUISITION_ROUTE"}

class Root1ClosureError(ValueError):
    pass

def _items(values: Iterable[Any]) -> set[str]:
    return {str(v).strip() for v in values if str(v).strip()}

def _f(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise Root1ClosureError(name.upper() + "_INVALID")
    try:
        return value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise Root1ClosureError(name.upper() + "_INVALID") from exc

def _digest(values: Iterable[Any]) -> str:
    payload = json.dumps(sorted(_items(values)), separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()

def classify_root1(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if not evidence or evidence.get("positive_operational_gap") is not True:
        return {
            "schema": SCHEMA,
            "status": "ROOT1_INACTIVE_NO_ACTION",
            "root1_active": False,
            "reason": "NO_POSITIVE_OPERATIONAL_CAPABILITY_GAP",
            "terminal_work_authorized": False,
        }
    required = {
        "constructive_witness_verified": True,
        "constructive_witness_content_addressed": True,
        "operative_failure_demonstrated": True,
        "acquisition_routes_accounted": True,
        "unresolved_after_available_acquisition": True,
    }
    missing = sorted(k for k, v in required.items() if evidence.get(k) is not v)
    behavior = str(evidence.get("required_behavior") or "").strip()
    if not behavior:
        missing.append("required_behavior")
    if missing:
        return {
            "schema": SCHEMA,
            "status": "ROOT1_NOT_ESTABLISHED",
            "root1_active": False,
            "reason": "UNKNOWN_OR_UNPROVED_IS_NOT_MISSING",
            "failed_requirements": sorted(set(missing)),
            "terminal_work_authorized": False,
        }
    return {
        "schema": SCHEMA,
        "status": "ROOT1_REOPENED_CONSTRUCTIVE_GAP",
        "root1_active": True,
        "required_behavior": behavior,
        "witness_id": str(evidence.get("witness_id") or "").strip() or None,
        "terminal_work_authorized": True,
    }

def minimum_capability_delta(
    *,
    required_primitives: Iterable[Any],
    verified_primitives: Iterable[Any],
    transfer_mappings: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    required = _items(required_primitives)
    verified = _items(verified_primitives)
    applied = transfer.apply(verified_facts=verified, mappings=transfer_mappings)
    covered = set(applied["verified_facts"])
    missing = sorted(required - covered)
    return {
        "schema": SCHEMA,
        "status": "DELTA_EMPTY" if not missing else "CAPABILITY_DELTA_OPEN",
        "required_primitives": sorted(required),
        "verified_or_proven_transfer_primitives": sorted(required & covered),
        "missing_primitives": missing,
        "delta_ratio": str(Fraction(len(missing), len(required))) if required else "0",
        "admitted_transfer_mappings": applied["admitted_transfer_mappings"],
    }

def _coverage_record_admissible(record: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if str(record.get("route_status") or "") not in COVERAGE_STATUSES:
        errors.append("ROUTE_STATUS_NOT_ADMISSIBLE")
    for key in ("independent_verified", "exact_byte_bound", "content_addressed", "target_brain_owned_configuration"):
        if record.get(key) is not True:
            errors.append(key.upper() + "_NOT_PROVEN")
    if record.get("future_use_requires_capability_rediscovery") is not False:
        errors.append("CAPABILITY_REDISCOVERY_REQUIRED")
    if _f(record.get("incremental_spend_usd", 0), "incremental_spend_usd") != 0:
        errors.append("INCREMENTAL_SPEND_NOT_ZERO")
    if str(record.get("route_status") or "") == "VERIFIED_ACQUISITION_ROUTE":
        for key in ("internalizable", "executable", "source_admission_verified"):
            if record.get(key) is not True:
                errors.append(key.upper() + "_NOT_PROVEN")
    if not str(record.get("route_id") or "").strip():
        errors.append("ROUTE_ID_REQUIRED")
    if not str(record.get("primitive_id") or "").strip():
        errors.append("PRIMITIVE_ID_REQUIRED")
    return (not errors, sorted(set(errors)))

def compile_frozen_envelope(
    *,
    envelope_id: str,
    required_primitives: Iterable[Any],
    coverage_records: Sequence[Mapping[str, Any]],
    envelope_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    eid = str(envelope_id or "").strip()
    required = _items(required_primitives)
    if not eid or not required:
        raise Root1ClosureError("NONEMPTY_ENVELOPE_AND_REQUIRED_PRIMITIVES_REQUIRED")
    expected_digest = _digest(required)
    receipt_ok = (
        envelope_receipt.get("independent_verified") is True
        and envelope_receipt.get("exact_byte_bound") is True
        and envelope_receipt.get("conclusion") == "success"
        and envelope_receipt.get("capability_set_complete") is True
        and str(envelope_receipt.get("envelope_id") or "").strip() == eid
        and str(envelope_receipt.get("primitive_set_sha256") or "").strip() == expected_digest
    )
    if not receipt_ok:
        raise Root1ClosureError("ENVELOPE_COMPLETENESS_RECEIPT_NOT_ADMISSIBLE")
    covered: dict[str, str] = {}
    rejected: list[dict[str, Any]] = []
    route_ids: set[str] = set()
    for record in coverage_records:
        rid = str(record.get("route_id") or "").strip()
        if rid and rid in route_ids:
            raise Root1ClosureError("DUPLICATE_ROUTE_ID:" + rid)
        if rid:
            route_ids.add(rid)
        ok, errors = _coverage_record_admissible(record)
        pid = str(record.get("primitive_id") or "").strip()
        if not ok:
            rejected.append({"primitive_id": pid or None, "route_id": rid or None, "errors": errors})
            continue
        if pid in required and pid not in covered:
            covered[pid] = rid
    uncovered = sorted(required - set(covered))
    sealed = not uncovered
    return {
        "schema": SCHEMA,
        "status": "ROOT1_CLOSED_FOR_FROZEN_ENVELOPE" if sealed else "ROOT1_ENVELOPE_COVERAGE_OPEN",
        "envelope_id": eid,
        "primitive_set_sha256": expected_digest,
        "required_primitive_count": len(required),
        "covered_primitive_count": len(covered),
        "uncovered_primitives": uncovered,
        "coverage_route_ids": {k: covered[k] for k in sorted(covered)},
        "rejected_records": rejected,
        "root1_sealed_for_frozen_envelope": sealed,
        "universal_semantic_learning_success_claimed": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }

def rank_acquisition_actions(actions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in actions:
        aid = str(raw.get("id") or "").strip()
        if not aid or aid in seen:
            raise Root1ClosureError("ACTION_ID_INVALID_OR_DUPLICATE")
        seen.add(aid)
        if raw.get("safe") is not True:
            continue
        if _f(raw.get("incremental_spend_usd", 0), "incremental_spend_usd") != 0:
            continue
        p = _f(raw.get("p_close", 0), "p_close")
        coverage = _f(raw.get("closure_mass", 0), "closure_mass")
        info = _f(raw.get("information_gain", 0), "information_gain")
        transfer_gain = _f(raw.get("transfer_gain", 0), "transfer_gain")
        proof_gain = _f(raw.get("proof_gain", 0), "proof_gain")
        time = _f(raw.get("time", 0), "time")
        risk = _f(raw.get("risk", 0), "risk")
        if p < 0 or p > 1 or min(coverage, info, transfer_gain, proof_gain, time, risk) < 0:
            raise Root1ClosureError("ACTION_DIMENSION_INVALID:" + aid)
        denom = time + risk
        if denom <= 0:
            raise Root1ClosureError("ACTION_TOTAL_COST_MUST_BE_POSITIVE:" + aid)
        expected = p * coverage + info + transfer_gain + proof_gain
        score = expected / denom
        if score <= 0:
            continue
        ranked.append({
            "id": aid,
            "source_class": str(raw.get("source_class") or "UNSPECIFIED").strip() or "UNSPECIFIED",
            "dependency_cluster": str(raw.get("dependency_cluster") or aid).strip() or aid,
            "route_kind": str(raw.get("route_kind") or "UNSPECIFIED").strip() or "UNSPECIFIED",
            "p_close": str(p),
            "expected_value": str(expected),
            "value_density": str(score),
            "incremental_spend_usd": "0",
        })
    ranked.sort(key=lambda x: (-Fraction(x["value_density"]), x["id"]))
    return ranked

def select_orthogonal_portfolio(
    actions: Sequence[Mapping[str, Any]],
    *,
    max_actions: int = 6,
    max_same_source_class: int = 1,
) -> list[dict[str, Any]]:
    if isinstance(max_actions, bool) or max_actions < 1:
        raise Root1ClosureError("MAX_ACTIONS_INVALID")
    ranked = rank_acquisition_actions(actions)
    selected: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    clusters: set[str] = set()
    for item in ranked:
        source = item["source_class"]
        cluster = item["dependency_cluster"]
        if source_counts.get(source, 0) >= max_same_source_class or cluster in clusters:
            continue
        selected.append(item)
        source_counts[source] = source_counts.get(source, 0) + 1
        clusters.add(cluster)
        if len(selected) >= max_actions:
            break
    return selected

def search_stop_decision(
    *,
    selected_route_id: str,
    required_source_classes: Iterable[Any],
    searched_source_classes: Iterable[Any],
    invariance_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    route = str(selected_route_id or "").strip()
    if not route:
        raise Root1ClosureError("SELECTED_ROUTE_ID_REQUIRED")
    required = _items(required_source_classes)
    searched = _items(searched_source_classes)
    remaining = sorted(required - searched)
    if not remaining:
        return {
            "schema": SCHEMA,
            "decision_complete": True,
            "reason": "ALL_REQUIRED_SOURCE_CLASSES_SEARCHED",
            "remaining_source_classes": [],
        }
    digest = _digest(remaining)
    receipt = invariance_receipt or {}
    ok = (
        receipt.get("independent_verified") is True
        and receipt.get("exact_byte_bound") is True
        and receipt.get("conclusion") == "success"
        and receipt.get("all_remaining_sources_action_invariant") is True
        and str(receipt.get("selected_route_id") or "").strip() == route
        and str(receipt.get("remaining_source_classes_sha256") or "").strip() == digest
    )
    return {
        "schema": SCHEMA,
        "decision_complete": bool(ok),
        "reason": "PROVED_RESIDUAL_ACTION_INVARIANCE" if ok else "SEARCH_MUST_CONTINUE_OR_ABSTAIN",
        "remaining_source_classes": remaining,
        "remaining_source_classes_sha256": digest,
    }

def mechanism_graph_frontier(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    relations = (
        "dependencies", "forks", "authors", "papers", "citations", "official_docs",
        "specifications", "issues", "pull_requests", "releases", "downstream_users",
        "package_registries", "community_discussions",
    )
    edges: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        cid = str(candidate.get("id") or "").strip()
        if not cid:
            raise Root1ClosureError("CANDIDATE_ID_REQUIRED")
        for relation in relations:
            for value in candidate.get(relation, []) or []:
                node = str(value).strip()
                if node:
                    edges.add((cid, relation, node))
    return [
        {"candidate_id": cid, "relation": relation, "node": node}
        for cid, relation, node in sorted(edges)
    ]

def acquisition_transaction(
    *,
    gap_evidence: Mapping[str, Any] | None,
    required_primitives: Iterable[Any],
    verified_primitives: Iterable[Any],
    transfer_mappings: Sequence[Mapping[str, Any]] = (),
    actions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    gate = classify_root1(gap_evidence)
    if not gate["root1_active"]:
        return {
            "schema": SCHEMA,
            "status": "NO_ACTION_ROOT1_INACTIVE",
            "gate": gate,
            "selected_actions": [],
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    delta = minimum_capability_delta(
        required_primitives=required_primitives,
        verified_primitives=verified_primitives,
        transfer_mappings=transfer_mappings,
    )
    if not delta["missing_primitives"]:
        return {
            "schema": SCHEMA,
            "status": "CONSTRUCTIVE_GAP_COLLAPSED_BY_EXISTING_OR_PROVEN_TRANSFER",
            "gate": gate,
            "delta": delta,
            "selected_actions": [],
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": "ACQUISITION_REQUIRED",
        "gate": gate,
        "delta": delta,
        "selected_actions": select_orthogonal_portfolio(actions),
        "fresh_reality_authority": False,
        "promotion_authority": False,
    }
