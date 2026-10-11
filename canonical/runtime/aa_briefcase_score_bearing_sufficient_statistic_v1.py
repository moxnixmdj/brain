from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_SCORE_BEARING_SUFFICIENT_STATISTIC_V1"
PUBLIC_CONTRACT_PATH = (
    "canonical/evidence/AA_BRIEFCASE_PUBLIC_INTERFACE_CONTRACT_20261011_V1.json"
)
PUBLIC_CONTRACT_BLOB = "32b44233529221ac6aa21132782690a1fbf0f748"


class TraceError(ValueError):
    pass


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def verify_sufficient_statistic(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TraceError("PAYLOAD_INVALID")
    if payload.get("benchmark") != "AA-Briefcase":
        raise TraceError("BENCHMARK_MISMATCH")
    if payload.get("version") != "1.1":
        raise TraceError("VERSION_MISMATCH")

    contract = payload.get("public_contract")
    if not isinstance(contract, Mapping):
        raise TraceError("PUBLIC_CONTRACT_INVALID")
    if contract.get("path") != PUBLIC_CONTRACT_PATH:
        raise TraceError("PUBLIC_CONTRACT_PATH_MISMATCH")
    if contract.get("git_blob_sha") != PUBLIC_CONTRACT_BLOB:
        raise TraceError("PUBLIC_CONTRACT_BLOB_MISMATCH")

    required = (
        "all_rubric_verdicts_included",
        "all_analytical_pairwise_verdicts_included",
        "all_presentation_pairwise_verdicts_included",
        "all_judge_assignments_included",
        "all_per_scope_crowd_bt_eta_included",
        "rubric_synthetic_head_to_head_state_included",
        "all_score_bearing_comparison_rows_included",
        "scope_membership_included",
        "anchor_identity_and_rating_included",
        "fit_reference_parameters_included",
        "score_clamp_and_postfit_rules_included",
    )
    for key in required:
        if payload.get(key) is not True:
            raise TraceError(key.upper() + "_NOT_INCLUDED")

    if payload.get("anchor_model") != "GPT-5.5 (medium)":
        raise TraceError("ANCHOR_MODEL_MISMATCH")
    if payload.get("anchor_elo") != 1000:
        raise TraceError("ANCHOR_ELO_MISMATCH")

    trace = payload.get("score_bearing_trace")
    if not isinstance(trace, Mapping):
        raise TraceError("TRACE_INVALID")
    if set(trace) != {
        "rubric",
        "analytical_quality",
        "presentation",
        "judge_state",
        "scorer_state",
    }:
        raise TraceError("TRACE_FIELDS_INVALID")

    trace_sha256 = _sha(trace)
    declared = payload.get("score_bearing_trace_sha256")
    if declared is not None and declared != trace_sha256:
        raise TraceError("TRACE_DIGEST_MISMATCH")

    return {
        "schema": SCHEMA,
        "status": "PASS_SCORE_BEARING_SUFFICIENT_STATISTIC",
        "verified": True,
        "scope_complete": True,
        "score_bearing_trace_sha256": trace_sha256,
        "private_task_text_required_after_trace_is_bound": False,
        "private_source_file_bytes_required_after_trace_is_bound": False,
        "submission_artifact_bytes_required_after_trace_is_bound": False,
        "complete_score_inputs_bound": True,
        "candidate_score_derived": False,
        "reference_score_substitution_proved": False,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }


def verify_trace_substitution(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TraceError("SUBSTITUTION_PAYLOAD_INVALID")
    if payload.get("benchmark") != "AA-Briefcase":
        raise TraceError("BENCHMARK_MISMATCH")
    if payload.get("version") != "1.1":
        raise TraceError("VERSION_MISMATCH")
    if payload.get("reference_model") != "Claude Opus 5.5 Max":
        raise TraceError("REFERENCE_MODEL_MISMATCH")
    if payload.get("frozen_reference_elo") != 1822:
        raise TraceError("REFERENCE_ELO_MISMATCH")

    for key in (
        "reference_subject_normalized_trace_sha256",
        "candidate_subject_normalized_trace_sha256",
        "non_subject_graph_sha256",
        "scorer_state_sha256",
        "scorer_equivariance_proof_sha256",
    ):
        if not _is_sha256(payload.get(key)):
            raise TraceError(key.upper() + "_INVALID")

    if (
        payload["reference_subject_normalized_trace_sha256"]
        != payload["candidate_subject_normalized_trace_sha256"]
    ):
        raise TraceError("SUBJECT_NORMALIZED_TRACE_MISMATCH")

    if payload.get("same_frozen_non_subject_graph") is not True:
        raise TraceError("NON_SUBJECT_GRAPH_NOT_IDENTICAL")
    if payload.get("same_frozen_scorer_state") is not True:
        raise TraceError("SCORER_STATE_NOT_IDENTICAL")
    if payload.get("mathematical_crowd_bt_label_equivariance_verified") is not True:
        raise TraceError("MATHEMATICAL_LABEL_EQUIVARIANCE_NOT_VERIFIED")
    if payload.get("owner_implementation_equivariance_or_unique_fit_verified") is not True:
        return {
            "schema": SCHEMA,
            "status": "OPEN_OWNER_IMPLEMENTATION_EQUIVARIANCE",
            "score_equality_proved": False,
            "threshold_1822_proved": False,
            "reason": (
                "The public Crowd-BT objective is label-equivariant, but exact owner "
                "implementation equivalence or unique fitted subject rating remains unbound."
            ),
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_EXACT_FROZEN_SCORE_SUBSTITUTION",
        "score_equality_proved": True,
        "derived_candidate_elo": 1822,
        "threshold_1822_proved": True,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
