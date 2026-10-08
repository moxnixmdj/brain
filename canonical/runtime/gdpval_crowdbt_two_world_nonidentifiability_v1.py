"""Analytic two-world non-identifiability witness for GDPval-AA style Crowd-BT.

For annotator quality eta > 1/2 and latent rating difference d = Brain - Opus,
Crowd-BT gives

    q_eta(d) = (1-eta) + (2*eta-1) * sigmoid(d).

Therefore q_eta(d) is strictly increasing in d. A dataset containing only
Brain-win observations against Opus has strictly increasing log-likelihood in d;
its supremum is attained as d -> +infinity. A dataset containing only Opus-win
observations has strictly decreasing log-likelihood in d; its supremum is attained
as d -> -infinity.

Artificial Analysis publicly states that GDPval-AA v2.1 fits Crowd-BT with
per-judge quality parameters learned from prior judgements, but does not publish
the fitted values or Brain-specific pairwise outcomes. Hence choosing the same
admissible eta values > 1/2 in two otherwise identical extensions and varying
only the previously unobserved Brain outcomes yields opposite Brain-vs-Opus
orderings. This proves the public pre-Brain scoring surface alone does not identify
Brain >= Opus.

This is an information lower-bound witness, not an owner score.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping


class TwoWorldError(ValueError):
    pass


DEFAULT_QUALITIES = {
    "Claude Opus 5": Fraction(9, 10),
    "GPT-5.6 Sol": Fraction(17, 20),
    "Gemini 3.8 Flash": Fraction(4, 5),
}


def _eta(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise TwoWorldError(f"{label}_BOOL_FORBIDDEN")
    try:
        q = value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise TwoWorldError(f"{label}_INVALID") from exc
    if not (Fraction(1, 2) < q <= 1):
        raise TwoWorldError(f"{label}_MUST_BE_IN_(1/2,1]")
    return q


def analyze(qualities: Mapping[str, Any] | None = None) -> dict[str, Any]:
    raw = DEFAULT_QUALITIES if qualities is None else qualities
    if not isinstance(raw, Mapping) or not raw:
        raise TwoWorldError("JUDGE_QUALITIES_REQUIRED")

    qs = {str(k): _eta(v, str(k)) for k, v in raw.items()}
    slopes = {k: 2 * eta - 1 for k, eta in qs.items()}
    all_positive = all(s > 0 for s in slopes.values())

    # q_eta(d) = (1-eta) + (2 eta - 1) sigma(d).
    # Since sigma'(d)>0 for every finite d and every slope is positive:
    #   all-Brain-win log likelihood sum log q_eta(d) strictly increases in d;
    #   all-Opus-win log likelihood sum log(1-q_eta(d)) strictly decreases in d.
    brain_win_world = {
        "observed_new_outcomes": "EVERY_PREVIOUSLY_UNOBSERVED_BRAIN_VS_OPUS_JUDGEMENT_IS_BRAIN_WIN",
        "likelihood_monotonicity_in_d": "STRICTLY_INCREASING",
        "mle_ordering_limit": "BRAIN_ABOVE_OPUS",
    }
    opus_win_world = {
        "observed_new_outcomes": "EVERY_PREVIOUSLY_UNOBSERVED_BRAIN_VS_OPUS_JUDGEMENT_IS_OPUS_WIN",
        "likelihood_monotonicity_in_d": "STRICTLY_DECREASING",
        "mle_ordering_limit": "BRAIN_BELOW_OPUS",
    }

    passed = all_positive
    return {
        "schema": "PROJECT_BRAIN_GDPVAL_CROWDBT_TWO_WORLD_NONIDENTIFIABILITY_ANALYTIC_RESULT_V2",
        "status": "PASS__OUTCOME_ONLY_TWO_WORLD_REVERSAL_PROVED" if passed else "FAIL_CLOSED",
        "crowd_bt_identity": "q_eta(d)=(1-eta)+(2*eta-1)*sigmoid(d)",
        "same_judge_qualities_in_both_worlds": {k: str(v) for k, v in qs.items()},
        "quality_slopes_2eta_minus_1": {k: str(v) for k, v in slopes.items()},
        "all_quality_slopes_positive": all_positive,
        "worlds": {
            "W_BRAIN_WIN": brain_win_world,
            "W_OPUS_WIN": opus_win_world,
        },
        "only_deliberate_world_difference": "PREVIOUSLY_UNOBSERVED_BRAIN_PAIRWISE_JUDGE_OUTCOMES",
        "public_fact_preservation": [
            "SAME_CROWD_BT_MODEL_FAMILY",
            "SAME_JUDGE_IDENTITIES",
            "SAME_JUDGE_QUALITY_VALUES",
            "SAME_PRE_BRAIN_OWNER_HISTORY_AND_ANCHOR_STATE",
            "ONLY_NEW_BRAIN_SPECIFIC_OUTCOMES_DIFFER",
        ],
        "consequence": "CURRENT_PUBLIC_PRE_BRAIN_SCORING_SURFACE_ALONE_CANNOT_DECIDE_BRAIN_GE_OPUS__BRAIN_SPECIFIC_OWNER_OUTCOMES_OR_A_SOUND_STRONGER_TARGET_RELATION_BRIDGE_IS_INFORMATION_THEORETICALLY_REQUIRED",
        "hard_nonclaims": [
            "NO_CLAIM_THE_CHOSEN_QUALITIES_EQUAL_THE_REAL_OWNER_FITS",
            "NO_CLAIM_EITHER_SYNTHETIC_EXTENSION_IS_THE_REAL_OWNER_EPOCH",
            "NO_BRAIN_GDPVAL_SCORE",
            "NO_TERMINAL_CREDIT",
        ],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(analyze(), indent=2, sort_keys=True))
