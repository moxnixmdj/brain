"""GDPval-AA rubric-to-owner non-implication witness.

This proves a narrow information statement, not a claim about the actual hidden prompt.

Bound public facts specify that GDPval-AA v2.1 uses blind pairwise rankings from
a fixed judge panel, but the exact pairwise judge prompt / message template and
the complete load-bearing submission presentation semantics are not bound.

Therefore even the premise "Brain satisfies every public OpenAI GDPval rubric"
does not, by itself, logically entail an owner pairwise win. Two extensions of
the same currently bound public surface can preserve the same rubric vector and
differ only in the unbound judge relation, yielding opposite preferences.

The witness is deliberately minimal and fail-closed. It deletes rubric-only
closure as a proof route; it does not say rubrics are irrelevant to capability.
"""
from __future__ import annotations

from typing import Any, Mapping


class RubricNonImplicationError(ValueError):
    pass


def prove(public_surface: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(public_surface, Mapping):
        raise RubricNonImplicationError("PUBLIC_SURFACE_INVALID")

    unknown = public_surface.get("not_yet_bound_fail_closed")
    pairwise = (
        public_surface.get("corrected_evaluator_identity", {})
        .get("pairwise_stage", {})
    )
    if not isinstance(unknown, Mapping) or not isinstance(pairwise, Mapping):
        raise RubricNonImplicationError("EXPECTED_OWNER_SURFACE_FIELDS_MISSING")

    prompt_unbound = unknown.get("exact_pairwise_judge_prompt_or_message_template") is False
    presentation_unbound = unknown.get("exact_submission_rendering_and_pairwise_presentation_recipe") is False
    blind_ranker_bound = pairwise.get("type") == "BLIND_LLM_JUDGE_PANEL"

    if not (prompt_unbound and presentation_unbound and blind_ranker_bound):
        return {
            "schema": "PROJECT_BRAIN_GDPVAL_RUBRIC_OWNER_NONIMPLICATION_RESULT_V1",
            "status": "FAIL_CLOSED__PREMISES_NOT_MET",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    # Same public rubric state in both worlds.
    common = {
        "brain_public_rubric_vector": "ALL_PUBLIC_RUBRIC_CRITERIA_SATISFIED",
        "opus_public_rubric_vector": "UNSPECIFIED_OR_ANY",
        "pairwise_panel_identity": pairwise.get("judges"),
        "pairwise_blinding": True,
        "crowd_bt_stage_unchanged": True,
    }

    # The only changed object is the currently unbound mapping from the presented
    # pair to a preference verdict. Both worlds remain compatible with the public
    # fact "a blind judge ranks the two submissions" because no stronger public
    # relation from rubric satisfaction to that verdict is bound.
    worlds = {
        "W_RUBRIC_MONOTONE": {
            **common,
            "unbound_pairwise_relation_extension": "PREFER_BRAIN_WHEN_BRAIN_SATISFIES_ALL_PUBLIC_RUBRICS",
            "brain_vs_opus": "BRAIN_WIN",
        },
        "W_STYLE_OR_OTHER_LATENT_FACTOR": {
            **common,
            "unbound_pairwise_relation_extension": "PREFER_OPUS_ON_A_NONRUBRIC_PRESENTATION_OR_QUALITY_FACTOR",
            "brain_vs_opus": "OPUS_WIN",
        },
    }

    return {
        "schema": "PROJECT_BRAIN_GDPVAL_RUBRIC_OWNER_NONIMPLICATION_RESULT_V1",
        "status": "PASS__PUBLIC_RUBRIC_SATISFACTION_DOES_NOT_LOGICALLY_DETERMINE_OWNER_PAIRWISE_VERDICT",
        "premises": {
            "blind_pairwise_panel_bound": blind_ranker_bound,
            "exact_pairwise_prompt_unbound": prompt_unbound,
            "exact_presentation_recipe_unbound": presentation_unbound,
        },
        "worlds": worlds,
        "same_public_rubric_state_in_both_worlds": True,
        "only_deliberate_difference": "UNBOUND_OWNER_PAIRWISE_RELATION_EXTENSION",
        "consequence": "RUBRIC_ONLY_SCOPE_COMPLETION_IS_NOT_A_SUFFICIENT_CERTIFICATE_FOR_GDPVAL_AA_OWNER_PAIRWISE_NONINFERIORITY",
        "closure_alternatives": [
            "BIND_A_SOUND_RUBRIC_TO_OWNER_PAIRWISE_IMPLICATION_OR_MONOTONICITY_THEOREM",
            "OBTAIN_OWNER_OR_OWNER_EQUIVALENT_BRAIN_PAIRWISE_EVIDENCE",
            "PROVE_A_STRONGER_JUDGE_INDEPENDENT_TARGET_RELATION",
            "MATCH_THE_FULL_TARGET_TRAJECTORY_LAW_UNDER_AN_UNCLASSIFIED_HIDDEN_EVALUATOR_FALLBACK",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_THE_REAL_OWNER_JUDGE_ACTUALLY_PREFERS_NONRUBRIC_STYLE_OVER_TASK_CORRECTNESS",
            "NO_CLAIM_PUBLIC_RUBRICS_ARE_USELESS",
            "NO_CLAIM_RUBRIC_SATISFACTION_CANNOT_BE_PART_OF_A_STRONGER_BRIDGE",
            "NO_GDPVAL_OR_TERMINAL_CREDIT",
        ],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
