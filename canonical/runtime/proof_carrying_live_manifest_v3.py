"""Proof-carrying live manifest V3.

V2 had the right shape but trusted opaque receipt hashes and allowed activation
from a caller-supplied manifest digest without recomputing the candidate.
V3 makes the candidate and activation evidence self-validating and keeps live
global authority separate from activation candidacy.

A V3 pass never mutates live state. It proves that a manifest is eligible for a
separate atomic live-authority transaction with rollback to the last-known-good
manifest.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_LIVE_MANIFEST_V3"
ACTIVATION_SCHEMA = "PROJECT_BRAIN_LIVE_MANIFEST_ACTIVATION_CANDIDATE_V3"
IMPROVEMENT_SCHEMA = "PROJECT_BRAIN_VERIFIED_IMPROVEMENT_LOOP_V2"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "activation_candidate": False,
        "activation_authority": False,
        "promotion_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def route_subject_digest(rec: Mapping[str, Any]) -> str:
    return _sha(
        {
            "capability_id": rec.get("capability_id"),
            "route_id": rec.get("route_id"),
            "request_predicate": rec.get("request_predicate"),
            "executor_binding": rec.get("executor_binding"),
            "acceptance_contract": rec.get("acceptance_contract"),
            "selector_proof_sha256": rec.get("selector_proof_sha256"),
            "executor_sha256": rec.get("executor_sha256"),
            "acceptance_contract_sha256": rec.get(
                "acceptance_contract_sha256"
            ),
            "dependency_hashes": sorted(rec.get("dependency_hashes") or []),
        }
    )


def verification_receipt_digest(receipt: Mapping[str, Any]) -> str:
    return _sha(
        {
            "independently_verified": receipt.get(
                "independently_verified"
            ),
            "verifier_id": receipt.get("verifier_id"),
            "subject_sha256": receipt.get("subject_sha256"),
            "result_sha256": receipt.get("result_sha256"),
            "pass": receipt.get("pass"),
        }
    )


def candidate_authority_digest(authority: Mapping[str, Any]) -> str:
    return _sha(
        {
            "valid": authority.get("valid"),
            "manifest_candidate_authority": authority.get(
                "manifest_candidate_authority"
            ),
            "authority_scope": authority.get("authority_scope"),
            "issuer_id": authority.get("issuer_id"),
            "subject_sha256": authority.get("subject_sha256"),
        }
    )


def _validate_improvement_receipt(
    receipt: Mapping[str, Any],
    *,
    route_id: str,
) -> tuple[bool, str]:
    if receipt.get("schema") != IMPROVEMENT_SCHEMA:
        return False, "IMPROVEMENT_SCHEMA_INVALID"
    if receipt.get("pass") is not True or receipt.get(
        "promotion_candidate"
    ) is not True:
        return False, "IMPROVEMENT_NOT_PROMOTION_CANDIDATE"
    if receipt.get("promotion_authority") is not False:
        return False, "IMPROVEMENT_PREMATURE_PROMOTION_AUTHORITY"
    if receipt.get("route_id") != route_id:
        return False, "IMPROVEMENT_ROUTE_ID_MISMATCH"
    core = {
        "episode_id": receipt.get("episode_id"),
        "subject_sha256": receipt.get("subject_sha256"),
        "route_id": receipt.get("route_id"),
        "route_manifest_sha256": receipt.get("route_manifest_sha256"),
        "phase_receipt_sha256": receipt.get("phase_receipt_sha256"),
        "phase_output_sha256": receipt.get("phase_output_sha256"),
        "neighbor_receipt_sha256": receipt.get(
            "neighbor_receipt_sha256"
        ),
        "compression_receipt_sha256": receipt.get(
            "compression_receipt_sha256"
        ),
    }
    if not all(
        _valid_sha(core[k])
        for k in (
            "subject_sha256",
            "route_manifest_sha256",
            "compression_receipt_sha256",
        )
    ):
        return False, "IMPROVEMENT_CORE_SHA_INVALID"
    if not _nonempty(core["episode_id"]):
        return False, "IMPROVEMENT_EPISODE_INVALID"
    if not isinstance(core["phase_receipt_sha256"], Mapping):
        return False, "IMPROVEMENT_PHASE_RECEIPTS_INVALID"
    if not isinstance(core["phase_output_sha256"], Mapping):
        return False, "IMPROVEMENT_PHASE_OUTPUTS_INVALID"
    neighbors = core["neighbor_receipt_sha256"]
    if (
        not isinstance(neighbors, list)
        or len(neighbors) < 2
        or any(not _valid_sha(x) for x in neighbors)
    ):
        return False, "IMPROVEMENT_NEIGHBORS_INVALID"
    if receipt.get("improvement_receipt_sha256") != _sha(core):
        return False, "IMPROVEMENT_RECEIPT_SELF_DIGEST_MISMATCH"
    return True, "OK"


def _validate_route(rec: Mapping[str, Any]) -> tuple[bool, str]:
    for key in (
        "capability_id",
        "route_id",
        "request_predicate",
        "executor_binding",
        "acceptance_contract",
    ):
        if not _nonempty(rec.get(key)):
            return False, "MISSING_" + key.upper()
    for key in (
        "selector_proof_sha256",
        "executor_sha256",
        "acceptance_contract_sha256",
    ):
        if not _valid_sha(rec.get(key)):
            return False, "INVALID_" + key.upper()
    deps = rec.get("dependency_hashes")
    if (
        not isinstance(deps, list)
        or len(deps) != len(set(deps))
        or any(not _valid_sha(x) for x in deps)
    ):
        return False, "DEPENDENCY_HASH_CLOSURE_INVALID"
    subject = route_subject_digest(rec)

    verification = rec.get("verification_receipt")
    if not isinstance(verification, Mapping):
        return False, "VERIFICATION_RECEIPT_MISSING"
    if (
        verification.get("pass") is not True
        or verification.get("independently_verified") is not True
        or not _nonempty(verification.get("verifier_id"))
        or verification.get("subject_sha256") != subject
        or not _valid_sha(verification.get("result_sha256"))
    ):
        return False, "VERIFICATION_RECEIPT_INVALID"
    if verification.get("sha256") != verification_receipt_digest(
        verification
    ):
        return False, "VERIFICATION_RECEIPT_SELF_DIGEST_MISMATCH"

    authority = rec.get("candidate_authority")
    if not isinstance(authority, Mapping):
        return False, "CANDIDATE_AUTHORITY_MISSING"
    if (
        authority.get("valid") is not True
        or authority.get("manifest_candidate_authority") is not True
        or authority.get("authority_scope") != "LIVE_MANIFEST_CANDIDACY"
        or not _nonempty(authority.get("issuer_id"))
        or authority.get("subject_sha256") != subject
    ):
        return False, "CANDIDATE_AUTHORITY_INVALID"
    if authority.get("sha256") != candidate_authority_digest(authority):
        return False, "CANDIDATE_AUTHORITY_SELF_DIGEST_MISMATCH"

    origin = rec.get("origin_class")
    if origin not in {"STATIC_VERIFIED", "LEARNED_V2"}:
        return False, "ORIGIN_CLASS_INVALID"
    if origin == "LEARNED_V2":
        improvement = rec.get("improvement_receipt")
        if not isinstance(improvement, Mapping):
            return False, "IMPROVEMENT_RECEIPT_MISSING"
        ok, reason = _validate_improvement_receipt(
            improvement,
            route_id=rec["route_id"],
        )
        if not ok:
            return False, reason
    elif rec.get("improvement_receipt") is not None:
        return False, "STATIC_ROUTE_MUST_NOT_CARRY_IMPROVEMENT_RECEIPT"

    if (
        rec.get("runtime_compatible") is not True
        or rec.get("revoked") is True
        or rec.get("deployable") is not True
    ):
        return False, "ROUTE_NOT_CANDIDATE_ELIGIBLE"
    return True, "OK"


def route_record_digest(rec: Mapping[str, Any]) -> str:
    verification = rec.get("verification_receipt") or {}
    authority = rec.get("candidate_authority") or {}
    improvement = rec.get("improvement_receipt")
    return _sha(
        {
            "capability_id": rec.get("capability_id"),
            "route_id": rec.get("route_id"),
            "request_predicate": rec.get("request_predicate"),
            "executor_binding": rec.get("executor_binding"),
            "acceptance_contract": rec.get("acceptance_contract"),
            "selector_proof_sha256": rec.get("selector_proof_sha256"),
            "executor_sha256": rec.get("executor_sha256"),
            "acceptance_contract_sha256": rec.get(
                "acceptance_contract_sha256"
            ),
            "verification_receipt_sha256": verification.get("sha256"),
            "candidate_authority_sha256": authority.get("sha256"),
            "dependency_hashes": sorted(rec.get("dependency_hashes") or []),
            "priority": int(rec.get("priority", 0)),
            "specificity": int(rec.get("specificity", 0)),
            "origin_class": rec.get("origin_class"),
            "improvement_receipt_sha256": (
                improvement.get("improvement_receipt_sha256")
                if isinstance(improvement, Mapping)
                else None
            ),
        }
    )


def _manifest_core(routes: list[dict[str, Any]]) -> dict[str, Any]:
    caps = sorted({x["capability_id"] for x in routes})
    return {
        "route_count": len(routes),
        "capability_ids": caps,
        "route_ids": [x["route_id"] for x in routes],
        "routes": routes,
    }


def compile_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    verified_deployable_capability_ids: Iterable[str],
) -> dict[str, Any]:
    rows = list(records)
    if any(not isinstance(x, Mapping) for x in rows):
        return _fail("RECORD_NOT_MAPPING")
    expected = {
        str(x)
        for x in verified_deployable_capability_ids
        if isinstance(x, str) and x
    }
    if not expected:
        return _fail("VERIFIED_DEPLOYABLE_SET_EMPTY")
    deployable = [x for x in rows if x.get("deployable") is True]
    actual_caps = {str(x.get("capability_id")) for x in deployable}
    if actual_caps != expected:
        return _fail(
            "VERIFIED_DEPLOYABLE_ACTIVE_SET_DRIFT",
            expected=sorted(expected),
            actual=sorted(actual_caps),
            missing=sorted(expected - actual_caps),
            extra=sorted(actual_caps - expected),
        )

    routes: list[dict[str, Any]] = []
    for rec in deployable:
        ok, reason = _validate_route(rec)
        if not ok:
            return _fail(
                "DEPLOYABLE_RECORD_NOT_PROOF_CARRYING",
                route_id=rec.get("route_id"),
                detail=reason,
            )
        route = {
            key: rec[key]
            for key in (
                "capability_id",
                "route_id",
                "request_predicate",
                "executor_binding",
                "acceptance_contract",
                "selector_proof_sha256",
                "executor_sha256",
                "acceptance_contract_sha256",
                "origin_class",
            )
        }
        route.update(
            {
                "route_subject_sha256": route_subject_digest(rec),
                "verification_receipt_sha256": rec[
                    "verification_receipt"
                ]["sha256"],
                "candidate_authority_sha256": rec[
                    "candidate_authority"
                ]["sha256"],
                "dependency_hashes": sorted(rec["dependency_hashes"]),
                "priority": int(rec.get("priority", 0)),
                "specificity": int(rec.get("specificity", 0)),
                "improvement_receipt_sha256": (
                    rec["improvement_receipt"][
                        "improvement_receipt_sha256"
                    ]
                    if rec["origin_class"] == "LEARNED_V2"
                    else None
                ),
                "route_record_sha256": route_record_digest(rec),
            }
        )
        routes.append(route)

    ids = [x["route_id"] for x in routes]
    if len(ids) != len(set(ids)):
        return _fail("DUPLICATE_ROUTE_ID")
    pred_exec: dict[str, set[str]] = {}
    for row in routes:
        pred_exec.setdefault(row["request_predicate"], set()).add(
            row["executor_binding"]
        )
    conflicts = sorted(
        key for key, values in pred_exec.items() if len(values) > 1
    )
    if conflicts:
        return _fail(
            "AMBIGUOUS_EXACT_PREDICATE_EXECUTOR_CONFLICT",
            predicates=conflicts,
        )
    routes.sort(
        key=lambda row: (
            -row["specificity"],
            -row["priority"],
            row["route_id"],
        )
    )
    core = _manifest_core(routes)
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__PROOF_CARRYING_MANIFEST_V3_COMPILED__"
            "NOT_ACTIVATED"
        ),
        "reason": None,
        **core,
        "manifest_sha256": _sha(core),
        "activation_candidate": False,
        "activation_authority": False,
        "promotion_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def validate_manifest(candidate: Mapping[str, Any]) -> tuple[bool, str]:
    if (
        not isinstance(candidate, Mapping)
        or candidate.get("schema") != SCHEMA
        or candidate.get("pass") is not True
    ):
        return False, "CANDIDATE_MANIFEST_INVALID"
    routes = candidate.get("routes")
    if not isinstance(routes, list) or not routes:
        return False, "CANDIDATE_ROUTES_INVALID"
    if candidate.get("route_count") != len(routes):
        return False, "CANDIDATE_ROUTE_COUNT_MISMATCH"
    if candidate.get("route_ids") != [x.get("route_id") for x in routes]:
        return False, "CANDIDATE_ROUTE_ID_LIST_MISMATCH"
    caps = sorted({x.get("capability_id") for x in routes})
    if candidate.get("capability_ids") != caps:
        return False, "CANDIDATE_CAPABILITY_SET_MISMATCH"
    for row in routes:
        if not isinstance(row, Mapping):
            return False, "CANDIDATE_ROUTE_ROW_INVALID"
        required_sha = (
            "route_subject_sha256",
            "verification_receipt_sha256",
            "candidate_authority_sha256",
            "route_record_sha256",
        )
        if any(not _valid_sha(row.get(k)) for k in required_sha):
            return False, "CANDIDATE_ROUTE_SHA_INVALID"
        deps = row.get("dependency_hashes")
        if not isinstance(deps, list) or any(
            not _valid_sha(x) for x in deps
        ):
            return False, "CANDIDATE_DEPENDENCY_HASH_INVALID"
    core = _manifest_core([dict(x) for x in routes])
    if candidate.get("manifest_sha256") != _sha(core):
        return False, "CANDIDATE_MANIFEST_SELF_DIGEST_MISMATCH"
    return True, "OK"


def canary_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha(
        {
            "route_id": row.get("route_id"),
            "manifest_sha256": row.get("manifest_sha256"),
            "route_record_sha256": row.get("route_record_sha256"),
            "pass": row.get("pass"),
            "independently_verified": row.get("independently_verified"),
            "verifier_id": row.get("verifier_id"),
            "result_sha256": row.get("result_sha256"),
        }
    )


def runtime_ack_digest(row: Mapping[str, Any]) -> str:
    return _sha(
        {
            "loaded": row.get("loaded"),
            "manifest_sha256": row.get("manifest_sha256"),
            "route_ids": sorted(row.get("route_ids") or []),
            "runtime_instance_sha256": row.get(
                "runtime_instance_sha256"
            ),
            "deployment_artifact_sha256": row.get(
                "deployment_artifact_sha256"
            ),
        }
    )


def replay_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha(
        {
            "route_id": row.get("route_id"),
            "manifest_sha256": row.get("manifest_sha256"),
            "route_record_sha256": row.get("route_record_sha256"),
            "pass": row.get("pass"),
            "through_normal_front_door": row.get(
                "through_normal_front_door"
            ),
            "independently_verified": row.get(
                "independently_verified"
            ),
            "verifier_id": row.get("verifier_id"),
            "result_sha256": row.get("result_sha256"),
        }
    )


def verify_activation_candidate(
    candidate: Mapping[str, Any],
    *,
    canary_receipts: Iterable[Mapping[str, Any]],
    runtime_ack: Mapping[str, Any],
    replay_receipts: Iterable[Mapping[str, Any]],
    previous_live_manifest_sha256: str,
) -> dict[str, Any]:
    base = {
        "schema": ACTIVATION_SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "activation_candidate": False,
        "activation_authority": False,
        "promotion_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        "rollback_required": True,
        "last_known_good_manifest_sha256": (
            previous_live_manifest_sha256
            if _valid_sha(previous_live_manifest_sha256)
            else None
        ),
    }
    if not _valid_sha(previous_live_manifest_sha256):
        return {**base, "reason": "LAST_KNOWN_GOOD_MANIFEST_INVALID"}

    ok, reason = validate_manifest(candidate)
    if not ok:
        return {**base, "reason": reason}

    routes = {
        row["route_id"]: row
        for row in candidate["routes"]
    }
    route_ids = set(routes)

    canary_rows = [
        row for row in canary_receipts if isinstance(row, Mapping)
    ]
    if len(canary_rows) != len(route_ids):
        return {**base, "reason": "CANARY_SET_NOT_EXACT"}
    canary = {str(row.get("route_id")): row for row in canary_rows}
    if set(canary) != route_ids or len(canary) != len(canary_rows):
        return {**base, "reason": "CANARY_SET_NOT_EXACT"}
    for route_id, row in canary.items():
        if (
            row.get("pass") is not True
            or row.get("independently_verified") is not True
            or not _nonempty(row.get("verifier_id"))
            or not _valid_sha(row.get("result_sha256"))
            or row.get("manifest_sha256") != candidate["manifest_sha256"]
            or row.get("route_record_sha256")
            != routes[route_id]["route_record_sha256"]
        ):
            return {
                **base,
                "reason": "CANARY_BINDING_INVALID",
                "route_id": route_id,
            }
        if row.get("receipt_sha256") != canary_receipt_digest(row):
            return {
                **base,
                "reason": "CANARY_RECEIPT_SELF_DIGEST_MISMATCH",
                "route_id": route_id,
            }

    if not isinstance(runtime_ack, Mapping):
        return {**base, "reason": "RUNTIME_ACK_INVALID"}
    if (
        runtime_ack.get("loaded") is not True
        or runtime_ack.get("manifest_sha256") != candidate["manifest_sha256"]
        or sorted(runtime_ack.get("route_ids") or [])
        != sorted(route_ids)
        or not _valid_sha(runtime_ack.get("runtime_instance_sha256"))
        or not _valid_sha(runtime_ack.get("deployment_artifact_sha256"))
    ):
        return {**base, "reason": "RUNTIME_ACK_INVALID"}
    if runtime_ack.get("receipt_sha256") != runtime_ack_digest(runtime_ack):
        return {**base, "reason": "RUNTIME_ACK_SELF_DIGEST_MISMATCH"}

    replay_rows = [
        row for row in replay_receipts if isinstance(row, Mapping)
    ]
    if len(replay_rows) != len(route_ids):
        return {**base, "reason": "REPLAY_SET_NOT_EXACT"}
    replays = {str(row.get("route_id")): row for row in replay_rows}
    if set(replays) != route_ids or len(replays) != len(replay_rows):
        return {**base, "reason": "REPLAY_SET_NOT_EXACT"}
    for route_id, row in replays.items():
        if (
            row.get("pass") is not True
            or row.get("through_normal_front_door") is not True
            or row.get("independently_verified") is not True
            or not _nonempty(row.get("verifier_id"))
            or not _valid_sha(row.get("result_sha256"))
            or row.get("manifest_sha256") != candidate["manifest_sha256"]
            or row.get("route_record_sha256")
            != routes[route_id]["route_record_sha256"]
        ):
            return {
                **base,
                "reason": "REPRESENTATIVE_REPLAY_BINDING_INVALID",
                "route_id": route_id,
            }
        if row.get("receipt_sha256") != replay_receipt_digest(row):
            return {
                **base,
                "reason": "REPLAY_RECEIPT_SELF_DIGEST_MISMATCH",
                "route_id": route_id,
            }

    core = {
        "candidate_manifest_sha256": candidate["manifest_sha256"],
        "previous_live_manifest_sha256": previous_live_manifest_sha256,
        "route_ids": sorted(route_ids),
        "route_record_sha256": sorted(
            routes[x]["route_record_sha256"] for x in route_ids
        ),
        "canary_receipt_sha256": sorted(
            canary[x]["receipt_sha256"] for x in route_ids
        ),
        "runtime_ack_receipt_sha256": runtime_ack["receipt_sha256"],
        "replay_receipt_sha256": sorted(
            replays[x]["receipt_sha256"] for x in route_ids
        ),
    }
    return {
        **base,
        "pass": True,
        "status": (
            "PASS__LIVE_MANIFEST_ACTIVATION_CANDIDATE_V3__"
            "SEPARATE_LIVE_GLOBAL_AUTHORITY_REQUIRED"
        ),
        "reason": None,
        "activation_candidate_receipt_sha256": _sha(core),
        "activation_candidate": True,
        "activation_authority": False,
        "promotion_authority": False,
        "rollback_required": False,
        "requires_live_global_authority": True,
        "candidate_manifest_sha256": candidate["manifest_sha256"],
    }
