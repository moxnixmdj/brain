from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CAPABILITY_INFORMATION_REDUCTION_V1"
BENCHMARK = "AA-Briefcase"
VERSION = "1.1"
REFERENCE_ELO = 1822
REFERENCE_ID = "OPUS_5_5_AA_BRIEFCASE_1822_REFERENCE"
REFERENCE_VECTOR_SHA256 = "1e542d27e3282755bfba0c33f9cfe1398fb71409df3b543848cada6ce2e94879"
SCORE_DIMENSIONS = frozenset({"RUBRIC", "ANALYTICAL_QUALITY", "PRESENTATION"})
FAILURE_CLASSES = frozenset({
    "RUBRIC_INFERIORITY",
    "ANALYTICAL_QUALITY_INFERIORITY",
    "PRESENTATION_INFERIORITY",
    "EXECUTION_INTERFACE_FAILURE",
})


class ReductionError(ValueError):
    pass


def _valid_sha256(value: Any) -> bool:
    s = str(value or "")
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def validate_target_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("benchmark") != BENCHMARK:
        raise ReductionError("BENCHMARK_MISMATCH")
    if contract.get("version") != VERSION:
        raise ReductionError("VERSION_MISMATCH")
    if contract.get("literal_audit_threshold_elo") != REFERENCE_ELO:
        raise ReductionError("LITERAL_AUDIT_THRESHOLD_MISMATCH")
    if contract.get("reference_id") != REFERENCE_ID:
        raise ReductionError("REFERENCE_ID_MISMATCH")
    if contract.get("reference_vector_sha256") != REFERENCE_VECTOR_SHA256:
        raise ReductionError("REFERENCE_VECTOR_MISMATCH")
    if contract.get("literal_score_is_primary") is not False:
        raise ReductionError("LITERAL_SCORE_MUST_BE_AUDIT_ONLY")
    if contract.get("capability_comparison_is_primary") is not True:
        raise ReductionError("CAPABILITY_COMPARISON_MUST_BE_PRIMARY")
    dims = contract.get("score_bearing_dimensions")
    if not isinstance(dims, list) or frozenset(map(str, dims)) != SCORE_DIMENSIONS:
        raise ReductionError("SCORE_DIMENSIONS_INCOMPLETE")
    if contract.get("literal_score_backpropagation_forbidden") is not True:
        raise ReductionError("LITERAL_SCORE_BACKPROPAGATION_GUARD_MISSING")


def _candidate_record(raw: Mapping[str, Any]) -> tuple[str, frozenset[str], float, str]:
    cid = str(raw.get("id") or "")
    if not cid:
        raise ReductionError("CANDIDATE_ID_MISSING")
    required_flags = ("verified", "causal", "generalization_bound", "subject_bound", "reference_bound")
    if not all(raw.get(k) is True for k in required_flags):
        raise ReductionError(f"CANDIDATE_NOT_ADMISSIBLE:{cid}")
    if raw.get("reference_id") != REFERENCE_ID:
        raise ReductionError(f"CANDIDATE_REFERENCE_MISMATCH:{cid}")
    if raw.get("reference_vector_sha256") != REFERENCE_VECTOR_SHA256:
        raise ReductionError(f"CANDIDATE_REFERENCE_VECTOR_MISMATCH:{cid}")
    subject_sha256 = str(raw.get("subject_sha256") or "")
    if not _valid_sha256(subject_sha256):
        raise ReductionError(f"CANDIDATE_SUBJECT_SHA256_INVALID:{cid}")
    covered_raw = raw.get("eliminates_failure_classes")
    if not isinstance(covered_raw, list):
        raise ReductionError(f"CANDIDATE_COVERAGE_INVALID:{cid}")
    covered = frozenset(map(str, covered_raw))
    if not covered or not covered <= FAILURE_CLASSES:
        raise ReductionError(f"CANDIDATE_COVERAGE_OUT_OF_DOMAIN:{cid}")
    cost = float(raw.get("action_cost", 1.0))
    if cost < 0:
        raise ReductionError(f"CANDIDATE_COST_NEGATIVE:{cid}")
    return cid, covered, cost, subject_sha256


def minimum_sufficient_basis(
    candidates: Sequence[Mapping[str, Any]],
    *,
    required_failure_classes: Iterable[str] = FAILURE_CLASSES,
) -> dict[str, Any]:
    required = frozenset(map(str, required_failure_classes))
    if not required or not required <= FAILURE_CLASSES:
        raise ReductionError("REQUIRED_FAILURE_CLASS_SET_INVALID")

    admissible = []
    rejected = []
    for raw in candidates:
        try:
            admissible.append(_candidate_record(raw))
        except ReductionError as exc:
            rejected.append({"id": str(raw.get("id") or ""), "reason": str(exc)})

    best = None
    for r in range(1, len(admissible) + 1):
        for combo in combinations(admissible, r):
            if len({x[3] for x in combo}) != 1:
                continue
            union = frozenset().union(*(x[1] for x in combo))
            if not required <= union:
                continue
            ids = tuple(sorted(x[0] for x in combo))
            total_cost = sum(x[2] for x in combo)
            key = (total_cost, len(combo), ids)
            if best is None or key < best[0]:
                best = (key, combo)

    if best is None:
        covered = frozenset().union(*(x[1] for x in admissible)) if admissible else frozenset()
        return {
            "schema": SCHEMA,
            "status": "OPEN__NO_COMPLETE_SAME_SUBJECT_ADMISSIBLE_BASIS",
            "capability_noninferiority_proved": False,
            "selected_certificate_ids": [],
            "missing_failure_classes": sorted(required - covered),
            "rejected_candidates": rejected,
            "literal_aa_elo_ge_1822_proved": False,
            "terminal_authority": False,
        }

    key, combo = best
    return {
        "schema": SCHEMA,
        "status": "PASS__MINIMUM_SUFFICIENT_SAME_SUBJECT_CAPABILITY_BASIS_SELECTED",
        "capability_noninferiority_proved": True,
        "selected_certificate_ids": sorted(x[0] for x in combo),
        "subject_sha256": combo[0][3],
        "reference_id": REFERENCE_ID,
        "reference_vector_sha256": REFERENCE_VECTOR_SHA256,
        "total_action_cost": key[0],
        "covered_failure_classes": sorted(required),
        "rejected_candidates": rejected,
        "literal_aa_elo_ge_1822_proved": False,
        "hard_nonclaim": "CAPABILITY_CERTIFICATE_DOES_NOT_IMPLY_LITERAL_REALIZED_AA_ELO_WITHOUT_A_SEPARATE_SCORE_BRIDGE",
        "terminal_authority": False,
    }


def current_evidence_probe() -> dict[str, Any]:
    candidates = [
        {
            "id": "PROFESSIONAL_PROPERTY_TRUTH_24_OF_24",
            "verified": True,
            "causal": True,
            "generalization_bound": True,
            "subject_bound": True,
            "reference_bound": False,
            "reference_id": REFERENCE_ID,
            "reference_vector_sha256": REFERENCE_VECTOR_SHA256,
            "subject_sha256": "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e",
            "eliminates_failure_classes": ["EXECUTION_INTERFACE_FAILURE"],
            "action_cost": 0,
        },
        {
            "id": "SELECTED_CELL_TOP_LAW_30_CASE",
            "verified": True,
            "causal": True,
            "generalization_bound": False,
            "subject_bound": True,
            "reference_bound": False,
            "reference_id": REFERENCE_ID,
            "reference_vector_sha256": REFERENCE_VECTOR_SHA256,
            "subject_sha256": "0" * 64,
            "eliminates_failure_classes": [
                "RUBRIC_INFERIORITY",
                "ANALYTICAL_QUALITY_INFERIORITY",
                "PRESENTATION_INFERIORITY",
            ],
            "action_cost": 0,
        },
    ]
    out = minimum_sufficient_basis(candidates)
    out["known_evidence_preserved"] = [
        "PROFESSIONAL_PROPERTY_TRUTH_24_OF_24",
        "SELECTED_CELL_TOP_LAW_30_CASE",
    ]
    out["next_action_class"] = (
        "BUILD_REFERENCE_BOUND_CAUSAL_GENERALIZATION_CERTIFICATE(S)_ON_ONE_EXACT_BRAIN_SUBJECT_"
        "THAT_ELIMINATE_THE_REMAINING_CAPABILITY_FAILURE_CLASSES_WITH_MINIMUM_TOTAL_ACTION_COST"
    )
    return out
