"""Derive complete bounded finance candidate terminal signatures from verified policy replays.

This module does not infer which candidate antecedent is true and does not prove
that the declared candidate set is semantically complete. It replays one bounded
verified finance policy family under every explicitly declared candidate Boolean.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import finance_normalized_unless_branch_v1 as unless_policy
from canonical.runtime import finance_normalized_if_branch_v1 as if_policy

SCHEMA = "PROJECT_BRAIN_FINANCE_CANDIDATE_POLICY_TERMINAL_SIGNATURES_V1"
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


def _validate_input(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if case.get("domain") != "FINANCE":
        raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")

    scope_id = str(case.get("scope_id") or "").strip()
    source_id = str(case.get("source_id") or "").strip()
    source_text = case.get("source_text")
    policy_family = str(case.get("policy_family") or "").strip().upper()
    bindings = case.get("candidate_fact_bindings")

    if not scope_id:
        raise ValueError("SCOPE_ID_REQUIRED")
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if policy_family not in SUPPORTED_POLICY_FAMILIES:
        raise ValueError("POLICY_FAMILY_UNSUPPORTED")
    if not isinstance(bindings, Mapping):
        raise ValueError("CANDIDATE_FACT_BINDINGS_REQUIRED")
    if not bindings or len(bindings) > MAX_CANDIDATES:
        raise ValueError("CANDIDATE_COUNT_INVALID")

    normalized: dict[str, bool] = {}
    for raw_id, raw_value in bindings.items():
        candidate_id = str(raw_id or "").strip()
        if not candidate_id or candidate_id in normalized:
            raise ValueError("CANDIDATE_ID_INVALID_OR_DUPLICATE")
        if not isinstance(raw_value, bool):
            raise ValueError("CANDIDATE_FACT_BOOLEAN_REQUIRED:" + candidate_id)
        normalized[candidate_id] = raw_value

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
            "schema": unless_policy.INPUT_SCHEMA,
            "source_id": checked["source_id"],
            "source_text": checked["source_text"],
            "exception_applies": fact,
        }
    if checked["policy_family"] == POLICY_IF:
        return {
            "schema": if_policy.INPUT_SCHEMA,
            "source_id": checked["source_id"],
            "source_text": checked["source_text"],
            "antecedent_holds": fact,
        }
    raise ValueError("POLICY_FAMILY_UNSUPPORTED")


def _run_policy(checked: Mapping[str, Any], fact: bool) -> dict[str, Any]:
    policy_case = _policy_case(checked, fact)
    if checked["policy_family"] == POLICY_UNLESS:
        result = unless_policy.compute(policy_case)
    elif checked["policy_family"] == POLICY_IF:
        result = if_policy.compute(policy_case)
    else:
        raise ValueError("POLICY_FAMILY_UNSUPPORTED")

    if result.get("pass") is not True:
        raise ValueError("POLICY_REPLAY_DID_NOT_PASS")
    if result.get("model_dependency_count") != 0:
        raise ValueError("POLICY_REPLAY_MODEL_DEPENDENCY_NONZERO")
    if result.get("scope_id") != checked["scope_id"]:
        raise ValueError("SCOPE_ID_MISMATCH")
    if result.get("source_text_sha256") != checked["source_text_sha256"]:
        raise ValueError("SOURCE_TEXT_HASH_MISMATCH")
    return dict(result)


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


def _equivalence_classes(
    terminal_signatures: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    buckets: dict[str, list[str]] = {}
    for candidate_id in sorted(terminal_signatures):
        digest = _sha(terminal_signatures[candidate_id])
        buckets.setdefault(digest, []).append(candidate_id)
    return [
        {
            "terminal_signature_sha256": digest,
            "candidate_ids": sorted(buckets[digest]),
        }
        for digest in sorted(buckets)
    ]


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    checked = _validate_input(case)

    policy_results: dict[str, dict[str, Any]] = {}
    terminal_signatures: dict[str, dict[str, Any]] = {}
    for candidate_id, fact in checked["candidate_fact_bindings"].items():
        replay = _run_policy(checked, fact)
        signature = _terminal_signature(checked, replay)
        policy_results[candidate_id] = replay
        terminal_signatures[candidate_id] = {
            "terminal_signature_complete": True,
            "terminal_signature": signature,
            "terminal_signature_sha256": _sha(signature),
        }

    bare = {
        cid: row["terminal_signature"]
        for cid, row in terminal_signatures.items()
    }
    classes = _equivalence_classes(bare)
    core = {
        "domain": "FINANCE",
        "scope_id": checked["scope_id"],
        "source_id": checked["source_id"],
        "source_text_sha256": checked["source_text_sha256"],
        "policy_family": checked["policy_family"],
        "candidate_ids": sorted(checked["candidate_fact_bindings"]),
        "candidate_count": len(checked["candidate_fact_bindings"]),
        "candidate_fact_bindings": checked["candidate_fact_bindings"],
        "policy_results": policy_results,
        "terminal_signatures": terminal_signatures,
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
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__DECLARED_CANDIDATE_POLICY_TERMINAL_SIGNATURES_DERIVED",
        "pass": True,
        **core,
        "result_sha256": _sha(core),
    }


def run(args: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return compute(args)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
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
