"""Verify the current causal reclassification of Escape Gap B.

This verifier grants no row, acceptance, or terminal authority. It only checks
that the exact immutable sources support the scheduling conclusion that no
currently active row satisfies the stricter Gap-B premise of one executable
action whose every allowed outcome terminalizes or strictly decreases a finite
well-founded acceptance-relevant measure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ESCAPE_ACTIVE_GAP_B_CAUSAL_RECLASSIFICATION_VERIFY_V1"
ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "reclassification": (
        "canonical/governance/ESCAPE_ACTIVE_GAP_B_CAUSAL_RECLASSIFICATION_20261010_V1.json",
        "c793b7f57b13a936646a2825cd67f26c28bf3744",
    ),
    "gdp_route": (
        "canonical/governance/GDPVAL_FIRST_RESIDUAL_MECHANICAL_ROUTE_EXPANSION_20261009_V2.json",
        "c38ca6ee010a63d6dc218aa2c9d85831e39441ed",
    ),
    "gdp_info": (
        "canonical/governance/GDPVAL_EVALUATION_LAW_MINIMUM_INFORMATION_CUT_20261008_V1.json",
        "7bf8b2ffc8186e14380da080e5a9832a2fd9a2a8",
    ),
    "chart_activation": (
        "canonical/governance/CHARTOGRAPHY_QWEN3_VL4B_VISION_ACQUISITION_ACTIVATION_V1.json",
        "d5b46fc2f784a206cda9bb7c6f1ee951300eccc0",
    ),
    "chart_preflight": (
        "canonical/verification/CHARTOGRAPHY_QWEN3VL4B_ZERO_CASE_PREFLIGHT_V2_RECONCILIATION_20261010_V1.json",
        "ea260cd10e29379fc148ec6f281e1006bf5bdbfa",
    ),
    "tb_reclass": (
        "canonical/governance/ESCAPE_TB_SCIENCE_CURRENT_ROUTE_RECLASSIFICATION_20261010_V2.json",
        "2639f4e58ef71502707ab6b2bb37efb592b1a234",
    ),
}


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _load_exact(root: Path, key: str) -> tuple[dict[str, Any], str]:
    rel, expected = SOURCES[key]
    data = (root / rel).read_bytes()
    actual = _git_blob_sha(data)
    if actual != expected:
        raise ValueError(f"{key}:GIT_BLOB_MISMATCH:{actual}")
    doc = json.loads(data.decode("utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{key}:JSON_OBJECT_REQUIRED")
    return doc, actual


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "detail": detail,
        "active_gap_b_count_verified": None,
        "row_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "terminal_authority": False,
    }


def evaluate(*, repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root)
    try:
        docs: dict[str, Mapping[str, Any]] = {}
        blobs: dict[str, str] = {}
        for key in SOURCES:
            docs[key], blobs[key] = _load_exact(root, key)

        rc = docs["reclassification"]
        if rc.get("status") != (
            "CAUSAL_RECLASSIFICATION__NO_CURRENT_ACTIVE_GAP_B_ROW_HAS_BOUND_"
            "ALL_OUTCOME_STRICT_PROGRESS__GDPVAL_AND_CHARTOGRAPHY_MOVE_TO_"
            "ACQUISITION_EVIDENCE_FRONTIER__TB_REMAINS_PARKED__ZERO_CREDIT"
        ):
            raise ValueError("RECLASSIFICATION_STATUS_INVALID")
        cut = rc.get("corrected_scheduler_cut")
        if not isinstance(cut, Mapping):
            raise ValueError("CORRECTED_SCHEDULER_CUT_REQUIRED")
        if cut.get("active_gap_b_count") != 0 or cut.get("active_gap_b_rows") != []:
            raise ValueError("ACTIVE_GAP_B_NOT_ZERO")
        if cut.get("effective_gap_a_active_count") != 12:
            raise ValueError("ACTIVE_GAP_A_COUNT_INVALID")
        if cut.get("parked_unresolved_rows") != ["TB_SCIENCE_GE_58_7"]:
            raise ValueError("PARKED_ROW_INVALID")
        if rc.get("accounting", {}).get("row_credit_delta") != 0:
            raise ValueError("RECLASSIFICATION_MUST_NOT_GRANT_ROW_CREDIT")

        gdp = docs["gdp_route"]
        if "ROUTE_AVAILABILITY_NOT_CRITERION_SATISFACTION" not in str(
            gdp.get("status")
        ).replace(" ", "_"):
            statement = str(gdp.get("theorem_boundary", {}).get("statement") or "")
            if "ROUTE_AVAILABILITY_NOT_CRITERION_SATISFACTION" not in statement.replace(" ", "_"):
                raise ValueError("GDP_ROUTE_BOUNDARY_MISSING")
        sched = json.dumps(gdp.get("scheduler_effect", []), sort_keys=True)
        if "WHEN_A_GDPVAL_CANDIDATE_OR_SCOPE_COMPLETE_CONSTRUCTIVE_PROOF_IS_AVAILABLE" not in sched:
            raise ValueError("GDP_CANDIDATE_CONDITIONAL_MISSING")
        if gdp.get("measured_effect", {}).get("remaining_unresolved_first_residuals") != 128:
            raise ValueError("GDP_RESIDUAL_COUNT_DRIFT")

        ginfo = docs["gdp_info"]
        if "PUBLIC_BOUND_FACTS_INSUFFICIENT_FOR_TARGET_RELATION" not in str(ginfo.get("status")):
            raise ValueError("GDP_INFORMATION_CUT_STATUS_INVALID")
        minimum = ginfo.get("minimum_separator_cut")
        if not isinstance(minimum, Mapping):
            raise ValueError("GDP_MINIMUM_SEPARATOR_CUT_REQUIRED")
        if "ONE_AUTHENTIC_FACT_OR_STRONGER_CERTIFICATE" not in str(
            minimum.get("required_form")
        ):
            raise ValueError("GDP_SEPARATOR_FRONTIER_INVALID")

        chart = docs["chart_preflight"]
        if chart.get("carrier", {}).get("conclusion") != "success":
            raise ValueError("CHART_PREFLIGHT_NOT_SUCCESS")
        observed = chart.get("observed")
        if not isinstance(observed, Mapping):
            raise ValueError("CHART_OBSERVED_REQUIRED")
        for key in (
            "model_hash_match",
            "projector_hash_match",
            "llama_mtmd_cli_build_pass",
            "model_and_projector_loaded_without_oom",
            "synthetic_multimodal_inference_exit_zero",
            "synthetic_answer_nonempty",
            "synthetic_answer_identified_red_and_blue",
        ):
            if observed.get(key) is not True:
                raise ValueError("CHART_PREFLIGHT_PREMISE_UNPROVED:" + key)
        if observed.get("terminal_cases_consumed") != 0:
            raise ValueError("CHART_TERMINAL_CASE_CONSUMPTION_NONZERO")
        if observed.get("incremental_spend_usd") != 0:
            raise ValueError("CHART_INCREMENTAL_SPEND_NONZERO")
        still_open = set(chart.get("still_open") or [])
        required_open = {
            "NONTERMINAL_SCOPE_RELEVANT_CHART_REASONING_QUALIFICATION",
            "PROJECT_SPECIFIC_GEMINI_3_5_FLASH_JUDGE_CAPACITY_RECEIPT",
            "THIN_OFFICIAL_CHARTOGRAPHY_ADAPTER_END_TO_END_BINDING",
            "CHARTOGRAPHY_THRESHOLD_CERTIFICATE_GE_89",
        }
        if still_open != required_open:
            raise ValueError("CHART_OPEN_FRONTIER_DRIFT")

        activation = docs["chart_activation"]
        preserve = set(activation.get("scheduler_delta", {}).get("preserve") or [])
        if "NONTERMINAL_SCOPE_RELEVANT_CHART_IMAGE_REASONING_QUALIFICATION" not in preserve:
            raise ValueError("CHART_QUALIFICATION_FRONTIER_MISSING")
        if "CHARTOGRAPHY_THRESHOLD_CERTIFICATE_GE_89" not in preserve:
            raise ValueError("CHART_THRESHOLD_FRONTIER_MISSING")

        tb = docs["tb_reclass"]
        if tb.get("current_truth", {}).get("current_executable_internal_action") is not False:
            raise ValueError("TB_CURRENT_EXECUTABLE_ACTION_NOT_FALSE")
        if tb.get("scheduling_effect", {}).get("remove_from_active_gap_b_internal_route_count") is not True:
            raise ValueError("TB_NOT_REMOVED_FROM_ACTIVE_GAP_B")

        rows = rc.get("row_reclassifications")
        if not isinstance(rows, list) or len(rows) != 2:
            raise ValueError("ROW_RECLASSIFICATION_COUNT_INVALID")
        ids = {row.get("obligation_id") for row in rows if isinstance(row, Mapping)}
        if ids != {"PROWORK_GDPVAL_GE_1846", "CHARTOGRAPHY_TOOLS_GE_89"}:
            raise ValueError("ROW_RECLASSIFICATION_IDS_INVALID")
        if any(
            row.get("corrected_current_class") != "GAP_A_ACQUISITION_TOTALITY"
            or row.get("row_credit") is not False
            for row in rows
            if isinstance(row, Mapping)
        ):
            raise ValueError("ROW_RECLASSIFICATION_SEMANTICS_INVALID")

        return {
            "schema": SCHEMA,
            "status": "PASS__CURRENT_CAUSAL_RECLASSIFICATION_VERIFIED__ACTIVE_GAP_B_ZERO",
            "pass": True,
            "verified_source_blobs": blobs,
            "active_gap_b_count_verified": 0,
            "effective_gap_a_active_count_verified": 12,
            "parked_unresolved_count_verified": 1,
            "reclassified_rows": sorted(ids),
            "parked_rows": ["TB_SCIENCE_GE_58_7"],
            "row_credit_delta": 0,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
            "terminal_authority": False,
            "boundary": (
                "SCHEDULING_CLASSIFICATION_ONLY__NO_GAP_A_ROW_ACQUIRABILITY_"
                "NO_CC_R3_AND_NO_GLOBAL_ESCAPE_PROGRESS_TOTALITY_PROVED"
            ),
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


if __name__ == "__main__":
    print(json.dumps(evaluate(), sort_keys=True))
