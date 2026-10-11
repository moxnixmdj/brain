from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CROWD_BT_EXCHANGE_DOMINANCE_V1"


class ExchangeError(ValueError):
    pass


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


def _num(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExchangeError(label + "_NOT_NUMERIC")
    out = float(value)
    if not 0.0 <= out <= 1.0:
        raise ExchangeError(label + "_OUT_OF_RANGE")
    return out


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ExchangeError(label + "_NOT_SEQUENCE")
    out = list(value)
    if any(not isinstance(x, Mapping) for x in out):
        raise ExchangeError(label + "_ROW_NOT_OBJECT")
    return out


def verify_exchange_dominance(cert: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(cert, Mapping):
        raise ExchangeError("CERT_NOT_OBJECT")

    required_true = (
        "fixed_quality_crowd_bt_eq5",
        "same_epoch_same_scorer",
        "all_brain_opus_incident_non_direct_comparisons_bijectively_matched",
        "no_unmatched_brain_or_opus_incident_comparisons",
        "comparison_roles_normalized_to_candidate_win",
        "brain_opus_symmetric_regularization",
        "finite_global_mle_exists",
    )
    for key in required_true:
        if cert.get(key) is not True:
            raise ExchangeError(key.upper() + "_NOT_PROVED")

    matched = _rows(cert.get("matched_comparisons"), "MATCHED_COMPARISONS")
    direct = _rows(cert.get("direct_brain_opus_comparisons", []), "DIRECT_COMPARISONS")
    if not matched and not direct:
        raise ExchangeError("NO_COMPARISON_EVIDENCE")

    strict_informative = False
    normalized_rows: list[dict[str, Any]] = []

    for i, row in enumerate(matched):
        opponent = str(row.get("opponent") or "").strip()
        judge = str(row.get("judge") or "").strip()
        if not opponent or not judge:
            raise ExchangeError(f"MATCHED_{i}_IDENTITY_INVALID")
        eta = _num(row.get("judge_quality"), f"MATCHED_{i}_JUDGE_QUALITY")
        if eta < 0.5:
            raise ExchangeError(f"MATCHED_{i}_JUDGE_QUALITY_BELOW_HALF")
        brain = _num(row.get("brain_outcome"), f"MATCHED_{i}_BRAIN_OUTCOME")
        opus = _num(row.get("opus_outcome"), f"MATCHED_{i}_OPUS_OUTCOME")
        if brain not in {0.0, 0.5, 1.0} or opus not in {0.0, 0.5, 1.0}:
            raise ExchangeError(f"MATCHED_{i}_OUTCOME_NOT_DISCRETE")
        if brain < opus:
            raise ExchangeError(f"MATCHED_{i}_BRAIN_OUTCOME_WORSE")
        if brain > opus and eta > 0.5:
            strict_informative = True
        normalized_rows.append(
            {
                "kind": "MATCHED_THIRD_PARTY",
                "opponent": opponent,
                "judge": judge,
                "judge_quality": eta,
                "brain_outcome": brain,
                "opus_outcome": opus,
            }
        )

    for i, row in enumerate(direct):
        judge = str(row.get("judge") or "").strip()
        if not judge:
            raise ExchangeError(f"DIRECT_{i}_JUDGE_INVALID")
        eta = _num(row.get("judge_quality"), f"DIRECT_{i}_JUDGE_QUALITY")
        if eta < 0.5:
            raise ExchangeError(f"DIRECT_{i}_JUDGE_QUALITY_BELOW_HALF")
        brain = _num(row.get("brain_outcome"), f"DIRECT_{i}_BRAIN_OUTCOME")
        if brain not in {0.0, 0.5, 1.0}:
            raise ExchangeError(f"DIRECT_{i}_OUTCOME_NOT_DISCRETE")
        if brain < 0.5:
            raise ExchangeError(f"DIRECT_{i}_BRAIN_LOSES")
        if brain > 0.5 and eta > 0.5:
            strict_informative = True
        normalized_rows.append(
            {
                "kind": "DIRECT_BRAIN_VS_OPUS",
                "judge": judge,
                "judge_quality": eta,
                "brain_outcome": brain,
            }
        )

    if not strict_informative:
        raise ExchangeError("NO_STRICT_INFORMATIVE_BRAIN_ADVANTAGE")

    comparator_floor = cert.get("same_fit_opus_rating_lower_bound")
    threshold_conclusion = False
    bound_floor = None
    if comparator_floor is not None:
        if isinstance(comparator_floor, bool) or not isinstance(comparator_floor, (int, float)):
            raise ExchangeError("SAME_FIT_OPUS_RATING_LOWER_BOUND_NOT_NUMERIC")
        bound_floor = float(comparator_floor)
        threshold_conclusion = bound_floor >= 1822.0

    material = {
        "matched_rows": normalized_rows,
        "same_fit_opus_rating_lower_bound": bound_floor,
        "scorer_model": "FIXED_QUALITY_CROWD_BT_EQ5_WITH_BRAIN_OPUS_SYMMETRIC_REGULARIZATION_AND_FINITE_GLOBAL_MLE",
    }

    return {
        "schema": SCHEMA,
        "status": "PASS__STRICT_MLE_RATING_ORDER",
        "brain_rating_strictly_greater_than_opus_in_same_bound_fit": True,
        "same_fit_opus_rating_lower_bound": bound_floor,
        "aa_briefcase_ge_1822_implied": threshold_conclusion,
        "proof": [
            "ASSUME_FOR_CONTRADICTION_R_BRAIN_LE_R_OPUS.",
            "FOR_EACH_MATCHED_THIRD_PARTY_EDGE__CROWD_BT_OBSERVED_WIN_PROBABILITY_IS_NONDECREASING_IN_RATING_WHEN_ETA_GE_HALF.",
            "SWAPPING_BRAIN_AND_OPUS_RATINGS_CHANGES_THE_PAIRED_LOG_LIKELIHOOD_BY_(Y_B-Y_O)*(LOGIT_Q_O-LOGIT_Q_B)__WHICH_IS_NONNEGATIVE_WHEN_Y_B_GE_Y_O.",
            "DIRECT_BRAIN_OPUS_ROWS_WITH_Y_B_GE_HALF_ARE_ALSO_NONWORSE_UNDER_THE_SWAP.",
            "AT_LEAST_ONE_STRICT_OUTCOME_WITH_ETA_GT_HALF_MAKES_THE_ORDER_STRICT_OR_GIVES_A_POSITIVE_ANTISYMMETRIC_SCORE_DIRECTION_AT_EQUAL_RATINGS.",
            "SYMMETRIC_REGULARIZATION_IS_UNCHANGED_BY_THE_SWAP.",
            "A_FINITE_GLOBAL_MLE_EXISTS_BY_BOUND_PREMISE__SO_THE_FITTED_RATINGS_ARE_WELL_DEFINED.",
            "THEREFORE_A_GLOBAL_MAXIMUM_CANNOT_HAVE_R_BRAIN_LE_R_OPUS.",
        ],
        "certificate_sha256": _sha(material),
        "hard_nonclaims": [
            "THIS_THEOREM_DOES_NOT_PROVE_THE_REQUIRED_MATCHED_REALIZED_OUTCOMES_EXIST.",
            "THIS_THEOREM_DOES_NOT_PROVE_A_FINITE_GLOBAL_MLE_EXISTS_FOR_THE_OWNER_FIT__THAT_IS_AN_INPUT_PREMISE.",
            "THIS_THEOREM_DOES_NOT_PROVE_ARTIFICIAL_ANALYSIS_USES_A_BOUND_SAME_FIT_OPUS_FLOOR_OF_1822.",
            "WITHOUT_A_SAME_FIT_OPUS_RATING_FLOOR_GE_1822_THE_THEOREM_PROVES_ONLY_RELATIVE_RATING_ORDER_NOT_THE_FROZEN_1822_THRESHOLD.",
        ],
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
