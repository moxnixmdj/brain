"""Independent verifier for bounded finance candidate terminal signatures V1.

Does not import the terminal-signature producer. It independently validates every
candidate policy replay with the existing producer-independent IF/UNLESS verifier
and reconstructs the terminal signatures and equivalence classes.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import finance_normalized_unless_verify_v1 as unless_verify
from canonical.runtime import finance_normalized_if_verify_v1 as if_verify

SCHEMA = "PROJECT_BRAIN_FINANCE_CANDIDATE_POLICY_TERMINAL_SIGNATURES_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_CANDIDATE_POLICY_WORLDSET_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_CANDIDATE_POLICY_TERMINAL_SIGNATURES_RESULT_V1"

POLICY_UNLESS = "NORMALIZED_UNLESS"
POLICY_IF = "NORMALIZED_IF"
SUPPORTED_POLICY_FAMILIES = {POLICY_UNLESS, POLICY_IF}
MAX_CANDIDATES = 64


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _text_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _validate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if case.get("domain") != "FINANCE":
        raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
    scope_id = str(case.get("scope_id") or "").strip()
    source_id = str(case.get("source_id") or "").strip()
    source_text = case.get("source_text")
    policy_family = str(case.get("policy_family") or "").strip().upper()
    bindings = case.get("candidate_fact_bindings")
    if not scope_id or not source_id:
        raise ValueError("SCOPE_OR_SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if policy_family not in SUPPORTED_POLICY_FAMILIES:
        raise ValueError("POLICY_FAMILY_UNSUPPORTED")
    if not isinstance(bindings, Mapping) or not bindings or len(bindings) > MAX_CANDIDATES:
        raise ValueError("CANDIDATE_FACT_BINDINGS_INVALID")
    normalized = {}
    for raw_id, value in bindings.items():
        candidate_id = str(raw_id or "").strip()
        if not candidate_id or candidate_id in normalized:
            raise ValueError("CANDIDATE_ID_INVALID_OR_DUPLICATE")
        if not isinstance(value, bool):
            raise ValueError("CANDIDATE_FACT_BOOLEAN_REQUIRED:" + candidate_id)
        normalized[candidate_id] = value
    return {
        "scope_id": scope_id,
        "source_id": source_id,
        "source_text": source_text,
        "source_text_sha256": _text_sha(source_text),
        "policy_family": policy_family,
        "candidate_fact_bindings": {
            key: normalized[key] for key in sorted(normalized)
        },
    }


def _policy_case(checked: Mapping[str, Any], fact: bool) -> dict[str, Any]:
    if checked["policy_family"] == POLICY_UNLESS:
        return {
            "schema": unless_verify.INPUT_SCHEMA,
            "source_id": checked["source_id"],
            "source_text": checked["source_text"],
            "exception_applies": fact,
        }
    return {
        "schema": if_verify.INPUT_SCHEMA,
        "source_id": checked["source_id"],
        "source_text": checked["source_text"],
        "antecedent_holds": fact,
    }


def _verify_policy(
    checked: Mapping[str, Any],
    fact: bool,
    policy_result: Mapping[str, Any],
) -> None:
    case = _policy_case(checked, fact)
    if checked["policy_family"] == POLICY_UNLESS:
        receipt = unless_verify.verify(case, policy_result)
    else:
        receipt = if_verify.verify(case, policy_result)
    if receipt.get("verified") is not True:
        raise ValueError("POLICY_REPLAY_INDEPENDENT_VERIFICATION_FAILED")
    if receipt.get("producer_independent") is not True:
        raise ValueError("POLICY_VERIFIER_NOT_PRODUCER_INDEPENDENT")
    if receipt.get("model_dependency_count") != 0:
        raise ValueError("POLICY_VERIFIER_MODEL_DEPENDENCY_NONZERO")


def _terminal_signature(
    checked: Mapping[str, Any],
    policy_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "policy_family": checked["policy_family"],
        "scope_id": checked["scope_id"],
        "source_text_sha256": checked["source_text_sha256"],
        "relation": str(policy_result.get("relation") or ""),
        "selected_branch": str(policy_result.get("selected_branch") or ""),
        "selected_span": policy_result.get("selected_span"),
        "selected_text": str(policy_result.get("selected_text") or ""),
        "selected_text_sha256": str(policy_result.get("selected_text_sha256") or ""),
    }


def _classes(signatures: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[str]] = {}
    for candidate_id in sorted(signatures):
        digest = _sha(signatures[candidate_id])
        buckets.setdefault(digest, []).append(candidate_id)
    return [
        {
            "terminal_signature_sha256": digest,
            "candidate_ids": sorted(buckets[digest]),
        }
        for digest in sorted(buckets)
    ]


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    try:
        checked = _validate_case(case)
        if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
            raise ValueError("RESULT_SCHEMA_INVALID")
        if result.get("pass") is not True:
            raise ValueError("RESULT_NOT_PASS")
        if result.get("status") != "PASS__DECLARED_CANDIDATE_POLICY_TERMINAL_SIGNATURES_DERIVED":
            raise ValueError("RESULT_STATUS_INVALID")

        ids = sorted(checked["candidate_fact_bindings"])
        if result.get("candidate_ids") != ids or result.get("candidate_count") != len(ids):
            raise ValueError("CANDIDATE_DOMAIN_MISMATCH")
        if result.get("candidate_fact_bindings") != checked["candidate_fact_bindings"]:
            raise ValueError("CANDIDATE_FACT_BINDING_MISMATCH")
        if result.get("scope_id") != checked["scope_id"]:
            raise ValueError("SCOPE_ID_MISMATCH")
        if result.get("source_id") != checked["source_id"]:
            raise ValueError("SOURCE_ID_MISMATCH")
        if result.get("source_text_sha256") != checked["source_text_sha256"]:
            raise ValueError("SOURCE_TEXT_HASH_MISMATCH")
        if result.get("policy_family") != checked["policy_family"]:
            raise ValueError("POLICY_FAMILY_MISMATCH")

        policy_results = result.get("policy_results")
        terminal_rows = result.get("terminal_signatures")
        if not isinstance(policy_results, Mapping) or set(policy_results) != set(ids):
            raise ValueError("POLICY_RESULT_COVERAGE_INVALID")
        if not isinstance(terminal_rows, Mapping) or set(terminal_rows) != set(ids):
            raise ValueError("TERMINAL_SIGNATURE_COVERAGE_INVALID")

        bare: dict[str, dict[str, Any]] = {}
        for candidate_id in ids:
            policy_result = policy_results[candidate_id]
            if not isinstance(policy_result, Mapping):
                raise ValueError("POLICY_RESULT_NOT_OBJECT:" + candidate_id)
            _verify_policy(
                checked,
                checked["candidate_fact_bindings"][candidate_id],
                policy_result,
            )
            if policy_result.get("scope_id") != checked["scope_id"]:
                raise ValueError("POLICY_SCOPE_ID_MISMATCH:" + candidate_id)
            if policy_result.get("source_text_sha256") != checked["source_text_sha256"]:
                raise ValueError("POLICY_SOURCE_HASH_MISMATCH:" + candidate_id)

            signature = _terminal_signature(checked, policy_result)
            row = terminal_rows[candidate_id]
            if not isinstance(row, Mapping):
                raise ValueError("TERMINAL_SIGNATURE_ROW_INVALID:" + candidate_id)
            if row.get("terminal_signature_complete") is not True:
                raise ValueError("TERMINAL_SIGNATURE_COMPLETENESS_FALSE:" + candidate_id)
            if row.get("terminal_signature") != signature:
                raise ValueError("TERMINAL_SIGNATURE_MISMATCH:" + candidate_id)
            if row.get("terminal_signature_sha256") != _sha(signature):
                raise ValueError("TERMINAL_SIGNATURE_HASH_MISMATCH:" + candidate_id)
            bare[candidate_id] = signature

        classes = _classes(bare)
        if result.get("terminal_equivalence_classes") != classes:
            raise ValueError("TERMINAL_EQUIVALENCE_CLASSES_MISMATCH")
        if result.get("terminal_equivalence_class_count") != len(classes):
            raise ValueError("TERMINAL_EQUIVALENCE_CLASS_COUNT_MISMATCH")
        if result.get("all_candidates_terminally_equivalent") is not (len(classes) == 1):
            raise ValueError("TERMINAL_EQUIVALENCE_FLAG_MISMATCH")

        required_false = {
            "declared_candidate_set_semantic_completeness_claimed",
            "candidate_fact_truth_inferred",
            "semantic_truth_authority",
            "policy_adequacy_authority",
            "execution_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        }
        for field in required_false:
            if result.get(field) is not False:
                raise ValueError("AUTHORITY_BOUNDARY_VIOLATION:" + field)
        if result.get("terminal_signature_domain_complete_relative_to_declared_candidate_set") is not True:
            raise ValueError("DECLARED_DOMAIN_COMPLETENESS_MISSING")
        if result.get("terminal_credit_delta") != 0:
            raise ValueError("TERMINAL_CREDIT_NONZERO")

        core = {
            "domain": "FINANCE",
            "scope_id": checked["scope_id"],
            "source_id": checked["source_id"],
            "source_text_sha256": checked["source_text_sha256"],
            "policy_family": checked["policy_family"],
            "candidate_ids": ids,
            "candidate_count": len(ids),
            "candidate_fact_bindings": checked["candidate_fact_bindings"],
            "policy_results": {cid: dict(policy_results[cid]) for cid in ids},
            "terminal_signatures": {cid: dict(terminal_rows[cid]) for cid in ids},
            "terminal_equivalence_classes": classes,
            "terminal_equivalence_class_count": len(classes),
            "all_candidates_terminally_equivalent": len(classes) == 1,
            "terminal_signature_domain_complete_relative_to_declared_candidate_set": True,
            "declared_candidate_set_semantic_completeness_claimed": False,
            "candidate_fact_truth_inferred": False,
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        if result.get("result_sha256") != _sha(core):
            raise ValueError("RESULT_DIGEST_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS__PRODUCER_INDEPENDENT_CANDIDATE_TERMINAL_SIGNATURE_RECOMPUTATION",
            "pass": True,
            "verified": True,
            "producer_independent": True,
            "terminal_signatures_verified": True,
            "candidate_count": len(ids),
            "terminal_equivalence_class_count": len(classes),
            "declared_candidate_set_semantic_completeness_claimed": False,
            "candidate_fact_truth_inferred": False,
            "verification_authority_mutated": False,
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "verified": False,
            "producer_independent": True,
            "reason": type(exc).__name__ + ":" + str(exc),
            "declared_candidate_set_semantic_completeness_claimed": False,
            "candidate_fact_truth_inferred": False,
            "verification_authority_mutated": False,
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
