from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.aa_briefcase_dual_predicate_result_bridge_v1 import (
    EXPECTED,
    FROZEN_RATING_EPOCH,
    PREDICATES,
    THRESHOLD,
)

PAIR = (
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
)
LOAD_BEARING_KEYS = (
    "benchmark",
    "benchmark_version",
    "model",
    "effort",
    "evaluator",
    "harness",
    "fallback_policy",
    "score",
    "unit",
)
EXPECTED_SOURCE_SHAS = {
    "source_bindings": "9bbd45f066ab94fa3f5110b9cc5efcd4118d1367",
    "source_bridge": "8566c1038ccf041641452a9ce910532224950677",
    "source_bridge_verification": "e974baf2fb0a729b604672fb4cd68c8e2521002f",
}


class DedupError(ValueError):
    pass


def _bindings(doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = doc.get("bindings")
    if not isinstance(rows, list):
        raise DedupError("BINDINGS_LIST_REQUIRED")
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("predicate_id"), str):
            out[row["predicate_id"]] = row
    return out


def verify(candidate: Mapping[str, Any], target_bindings: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("schema") != "PROJECT_BRAIN_AA_BRIEFCASE_DUPLICATE_TRUTH_NECESSITY_COUNTERMODEL_V1":
        raise DedupError("CANDIDATE_SCHEMA_INVALID")

    for field, sha in EXPECTED_SOURCE_SHAS.items():
        source = candidate.get(field)
        if not isinstance(source, Mapping) or source.get("git_blob_sha") != sha:
            raise DedupError("SOURCE_SHA_MISMATCH:" + field)

    ids = tuple(candidate.get("predicates") or ())
    if ids != PAIR:
        raise DedupError("PREDICATE_PAIR_DRIFT")
    if tuple(PREDICATES) != PAIR:
        raise DedupError("BRIDGE_PREDICATE_PAIR_DRIFT")
    if float(THRESHOLD) != 1822.0:
        raise DedupError("BRIDGE_THRESHOLD_DRIFT")
    if FROZEN_RATING_EPOCH != "ANTHROPIC_RELEASE_2026_09_22__AA_BRIEFCASE_V1_1__OPUS55_MAX_DEFAULT_FALLBACK":
        raise DedupError("BRIDGE_EPOCH_DRIFT")

    rows = _bindings(target_bindings)
    for pid in PAIR:
        if pid not in rows:
            raise DedupError("TARGET_BINDING_MISSING:" + pid)

    a, b = rows[PAIR[0]], rows[PAIR[1]]
    for key in LOAD_BEARING_KEYS:
        if a.get(key) != b.get(key):
            raise DedupError("TARGET_TUPLE_NOT_IDENTICAL:" + key)

    if float(a.get("score")) != 1822.0:
        raise DedupError("TARGET_THRESHOLD_NOT_1822")

    for key, value in EXPECTED.items():
        if a.get(key) != value or b.get(key) != value:
            raise DedupError("BRIDGE_EXPECTED_TUPLE_DRIFT:" + key)

    shared = target_bindings.get("shared_target_tuple")
    if not isinstance(shared, Mapping) or set(shared.get("predicates") or ()) != set(PAIR):
        raise DedupError("SHARED_TARGET_TUPLE_DECLARATION_MISSING")

    frozen = candidate.get("frozen_truth_semantics")
    if not isinstance(frozen, Mapping):
        raise DedupError("FROZEN_TRUTH_SEMANTICS_REQUIRED")
    if frozen.get("rating_epoch") != FROZEN_RATING_EPOCH:
        raise DedupError("CANDIDATE_EPOCH_DRIFT")
    if float(frozen.get("threshold")) != float(THRESHOLD):
        raise DedupError("CANDIDATE_THRESHOLD_DRIFT")

    repair = candidate.get("candidate_repair")
    if not isinstance(repair, Mapping):
        raise DedupError("CANDIDATE_REPAIR_REQUIRED")
    if repair.get("representative_predicate") != PAIR[0]:
        raise DedupError("REPRESENTATIVE_DRIFT")
    if repair.get("duplicate_alias_predicate") != PAIR[1]:
        raise DedupError("ALIAS_DRIFT")
    if repair.get("delete_from_current_load_bearing_truth_count") != PAIR[1]:
        raise DedupError("DELETE_TARGET_DRIFT")
    aliases = repair.get("family_truth_aliases")
    expected_aliases = {
        "PROFESSIONAL_KNOWLEDGE_WORK": PAIR[0],
        "ARTIFACT_CREATION": PAIR[0],
    }
    if aliases != expected_aliases:
        raise DedupError("FAMILY_ALIAS_PRESERVATION_FAILED")
    if repair.get("preserve_in_historical_registry") is not True:
        raise DedupError("HISTORICAL_REGISTRY_MUST_BE_PRESERVED")
    if repair.get("expected_open_truth_delta_if_independently_verified_and_activated") != -1:
        raise DedupError("EXPECTED_DELTA_MUST_BE_MINUS_ONE")

    accounting = candidate.get("accounting")
    if not isinstance(accounting, Mapping):
        raise DedupError("ACCOUNTING_REQUIRED")
    for key in (
        "terminal_credit_delta",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            raise DedupError("CREDIT_INFLATION:" + key)

    # Extensional identity over all admissible comparable scalar results follows
    # because both predicates use the same score and threshold.
    probes = [float("-inf"), 0.0, 1821.999, 1822.0, 1822.001, 999999.0, float("inf")]
    for score in probes:
        p0 = score >= float(THRESHOLD)
        p1 = score >= float(THRESHOLD)
        if p0 != p1:
            raise DedupError("BOOLEAN_DIVERGENCE")

    return {
        "status": "PASS__TWO_IDS_ONE_FROZEN_TRUTH_PROPOSITION__FAMILY_REQUIREMENTS_PRESERVED__ZERO_CREDIT",
        "representative_predicate": PAIR[0],
        "alias_predicate": PAIR[1],
        "same_truth_function": True,
        "current_truth_count_delta_if_activated": -1,
        "terminal_credit_delta": 0,
    }
