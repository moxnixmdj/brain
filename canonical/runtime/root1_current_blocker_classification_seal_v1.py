from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ROOT1_CURRENT_BLOCKER_CLASSIFICATION_SEAL_V1"

class Root1SealError(ValueError):
    pass

def _rows(value: Any, name: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Root1SealError(name.upper() + "_ROWS_REQUIRED")
    if any(not isinstance(x, Mapping) for x in value):
        raise Root1SealError(name.upper() + "_ROW_INVALID")
    return value

def _required_int(mapping: Mapping[str, Any], key: str) -> int:
    if key not in mapping or isinstance(mapping.get(key), bool):
        raise Root1SealError(key.upper() + "_INTEGER_REQUIRED")
    try:
        return int(mapping[key])
    except Exception as exc:
        raise Root1SealError(key.upper() + "_INTEGER_REQUIRED") from exc

def _unique_ids(rows: Sequence[Mapping[str, Any]], key: str, name: str) -> set[str]:
    out: set[str] = set()
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            raise Root1SealError(name.upper() + "_ID_REQUIRED")
        if value in out:
            raise Root1SealError(name.upper() + "_DUPLICATE:" + value)
        out.add(value)
    return out

def compute_current_root1_blocker_seal(
    *,
    target_envelope: Mapping[str, Any],
    terminal_manifest: Mapping[str, Any],
    predicate_registry: Mapping[str, Any],
    evidence_ledger: Mapping[str, Any],
    root_state: Mapping[str, Any],
) -> dict[str, Any]:
    envelope_rows = _rows(target_envelope.get("families"), "envelope")
    manifest_rows = _rows(terminal_manifest.get("families"), "manifest")
    predicate_rows = _rows(predicate_registry.get("predicates"), "predicate")
    claim_rows = _rows(evidence_ledger.get("claims"), "claim")

    envelope_ids = _unique_ids(envelope_rows, "id", "envelope")
    manifest_ids = _unique_ids(manifest_rows, "id", "manifest")
    predicate_ids = _unique_ids(predicate_rows, "id", "predicate")

    declared_target_count = int(target_envelope.get("target_family_count") or 0)
    expected_manifest_count = int(terminal_manifest.get("expected_family_count") or 0)
    actual_manifest_count = int(terminal_manifest.get("actual_family_count") or 0)

    if declared_target_count <= 0:
        raise Root1SealError("TARGET_FAMILY_COUNT_INVALID")
    if not (
        declared_target_count
        == expected_manifest_count
        == actual_manifest_count
        == len(envelope_ids)
        == len(manifest_ids)
    ):
        raise Root1SealError("TERMINAL_FAMILY_COUNT_DRIFT")
    if envelope_ids != manifest_ids:
        raise Root1SealError("TERMINAL_FAMILY_IDENTITY_DRIFT")

    proved: set[str] = set()
    seen_claim_ids: set[str] = set()
    for row in claim_rows:
        pid = str(row.get("predicate_id") or "").strip()
        if not pid:
            raise Root1SealError("CLAIM_PREDICATE_ID_REQUIRED")
        if pid not in predicate_ids:
            raise Root1SealError("CLAIM_OUTSIDE_REGISTRY:" + pid)
        if pid in seen_claim_ids:
            raise Root1SealError("DUPLICATE_CLAIM:" + pid)
        seen_claim_ids.add(pid)
        if row.get("state") == "PROVED":
            if row.get("scope_complete") is not True:
                raise Root1SealError("PROVED_WITHOUT_SCOPE_COMPLETE:" + pid)
            if row.get("independent_or_objective") is not True:
                raise Root1SealError("PROVED_WITHOUT_INDEPENDENT_OR_OBJECTIVE_EVIDENCE:" + pid)
            proved.add(pid)

    unresolved = predicate_ids - proved

    current_acceptance = root_state.get("current_acceptance")
    if not isinstance(current_acceptance, Mapping):
        raise Root1SealError("CURRENT_ACCEPTANCE_REQUIRED")
    if _required_int(current_acceptance, "total_families") != declared_target_count:
        raise Root1SealError("ROOT_STATE_FAMILY_COUNT_DRIFT")
    if _required_int(current_acceptance, "total_atomic") != len(predicate_ids):
        raise Root1SealError("ROOT_STATE_ATOMIC_COUNT_DRIFT")
    if _required_int(current_acceptance, "proved_atomic") != len(proved):
        raise Root1SealError("ROOT_STATE_PROVED_COUNT_DRIFT")
    if _required_int(current_acceptance, "unresolved_atomic") != len(unresolved):
        raise Root1SealError("ROOT_STATE_UNRESOLVED_COUNT_DRIFT")

    partition = root_state.get("current_residual_root_partition")
    if not isinstance(partition, Mapping):
        raise Root1SealError("ROOT_PARTITION_REQUIRED")

    r2 = set(str(x) for x in partition.get("root2_only", ()))
    r3 = set(str(x) for x in partition.get("root3_only", ()))
    mixed = set(str(x) for x in partition.get("root2_and_root3", ()))

    if not r2.isdisjoint(r3) or not r2.isdisjoint(mixed) or not r3.isdisjoint(mixed):
        raise Root1SealError("ROOT_PARTITION_BUCKETS_NOT_DISJOINT")
    classified = r2 | r3 | mixed
    if classified != unresolved:
        missing = sorted(unresolved - classified)
        extra = sorted(classified - unresolved)
        raise Root1SealError(
            "ROOT_PARTITION_NOT_EXHAUSTIVE:"
            + "MISSING=" + ",".join(missing)
            + ";EXTRA=" + ",".join(extra)
        )

    if _required_int(partition, "unresolved_total") != len(unresolved):
        raise Root1SealError("ROOT_PARTITION_UNRESOLVED_COUNT_DRIFT")
    if _required_int(partition, "root2_only_count") != len(r2):
        raise Root1SealError("ROOT2_COUNT_DRIFT")
    if _required_int(partition, "root3_only_count") != len(r3):
        raise Root1SealError("ROOT3_COUNT_DRIFT")
    if _required_int(partition, "root2_and_root3_count") != len(mixed):
        raise Root1SealError("MIXED_COUNT_DRIFT")
    if _required_int(partition, "root1_positive_gap_count") != 0:
        raise Root1SealError("ROOT1_POSITIVE_GAP_COUNT_NONZERO")

    roots = root_state.get("roots")
    if not isinstance(roots, Mapping):
        raise Root1SealError("ROOTS_REQUIRED")
    root1 = roots.get("root_1_capability_missing")
    if not isinstance(root1, Mapping):
        raise Root1SealError("ROOT1_STATE_REQUIRED")
    blockers = root1.get("current_positive_root1_blockers")
    if blockers != []:
        raise Root1SealError("ROOT1_POSITIVE_BLOCKERS_NONEMPTY")

    root1_residual = unresolved - classified
    if root1_residual:
        raise Root1SealError("ROOT1_RESIDUAL_NONEMPTY")

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_TERMINAL_BLOCKER_SPACE_EXHAUSTIVELY_R2_R3__ROOT1_RESIDUAL_ZERO",
        "target_family_count": len(envelope_ids),
        "atomic_predicate_count": len(predicate_ids),
        "proved_predicate_count": len(proved),
        "unresolved_predicate_count": len(unresolved),
        "root2_only_count": len(r2),
        "root3_only_count": len(r3),
        "root2_and_root3_count": len(mixed),
        "root1_positive_gap_count": 0,
        "root1_current_blocker_residual_count": 0,
        "root1_current_blocker_residual_ids": [],
        "current_root1_classification_sealed": True,
        "current_root1_active": False,
        "reopen_rule": "ANY_NEW_CONSTRUCTIVE_VERIFIED_CONTENT_ADDRESSED_OPERATIVE_CAPABILITY_GAP_INVALIDATES_THIS_SEAL_AND_REOPENS_ROOT1",
        "seal_scope": "CURRENT_FROZEN_TERMINAL_ENVELOPE_AND_CURRENT_EVIDENCE_LEDGER_ONLY",
        "hard_nonclaims": [
            "NO_UNIVERSAL_SEMANTIC_LEARNING_SUCCESS_CLAIM",
            "NO_CLAIM_THAT_EVERY_POSSIBLE_CAPABILITY_IS_ACQUIRABLE",
            "NO_CLAIM_THAT_ALL_WORLD_DATA_IS_REACHABLE",
            "NO_OPUS55_PERFORMANCE_ACCEPTANCE_CREDIT",
            "NO_SCOPE_COMPLETENESS_CREDIT_FOR_ROOT2_OR_ROOT3",
            "NO_OWNERSHIP_PROMOTION",
            "NO_CLAIM_THAT_ROUTE_COVERAGE_IS_VERIFIED_FOR_ALL_OPEN_FAMILIES",
            "NO_CLAIM_THAT_FUTURE_EVIDENCE_CANNOT_REOPEN_ROOT1",
        ],
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
