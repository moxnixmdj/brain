from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.distributional_target_upper_envelope_v1 import weakly_dominates


class TargetLawResidualError(ValueError):
    pass


def _law(row: Mapping[str, Any]) -> Mapping[str, float]:
    law=row.get("law")
    if not isinstance(law, Mapping) or not law:
        raise TargetLawResidualError("LAW_REQUIRED")
    return law


def target_law_residual(
    brain_law: Mapping[str, float],
    possible_target_laws: Sequence[Mapping[str, Any]],
    *,
    evaluators: Sequence[Mapping[str, float]],
    hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not isinstance(brain_law, Mapping) or not brain_law:
        raise TargetLawResidualError("BRAIN_LAW_REQUIRED")
    if not isinstance(possible_target_laws, Sequence) or isinstance(possible_target_laws,(str,bytes)) or not possible_target_laws:
        raise TargetLawResidualError("POSSIBLE_TARGET_LAWS_REQUIRED")
    if not evaluators:
        raise TargetLawResidualError("COMPLETE_EVALUATOR_SEMANTICS_REQUIRED")

    dominated=[]
    residual=[]
    seen=set()
    for row in possible_target_laws:
        if not isinstance(row,Mapping):
            raise TargetLawResidualError("TARGET_LAW_ROW_INVALID")
        law_id=str(row.get("id") or "")
        if not law_id or law_id in seen:
            raise TargetLawResidualError("UNIQUE_TARGET_LAW_ID_REQUIRED")
        seen.add(law_id)
        law=_law(row)
        ok=weakly_dominates(
            brain_law,
            law,
            evaluators=evaluators,
            hard_constraints=hard_constraints,
        )
        (dominated if ok else residual).append(law_id)

    return {
        "possible_target_law_count":len(seen),
        "dominated_candidate_ids":sorted(dominated),
        "undominated_residual_ids":sorted(residual),
        "undominated_residual_count":len(residual),
        "comparator_or_structural_target_information_required":bool(residual),
        "comparator_free_positive_certificate":not residual,
        "exact_target_identity_required":False,
        "information_goal":"PROVE_ACTUAL_TARGET_LAW_NOT_IN_UNDOMINATED_RESIDUAL",
        "terminal_credit_delta":0,
    }


def target_restriction_suffices(
    residual_ids: Sequence[str],
    *,
    excluded_target_ids: Sequence[str],
) -> bool:
    residual=set(map(str,residual_ids))
    excluded=set(map(str,excluded_target_ids))
    return residual <= excluded


def finite_two_world_falsifier(
    brain_law: Mapping[str,float],
    possible_target_laws: Sequence[Mapping[str,Any]],
    *,
    evaluators: Sequence[Mapping[str,float]],
    hard_constraints: Sequence[Mapping[str,Any]] = (),
) -> dict[str,Any]:
    out=target_law_residual(
        brain_law,
        possible_target_laws,
        evaluators=evaluators,
        hard_constraints=hard_constraints,
    )
    dominated=set(out["dominated_candidate_ids"])
    residual=set(out["undominated_residual_ids"])
    if not residual:
        return {
            "countermodel_exists":False,
            "reason":"BRAIN_DOMINATES_ALL_CURRENTLY_POSSIBLE_TARGET_LAWS",
            **out,
        }
    if dominated:
        return {
            "countermodel_exists":True,
            "terminal_true_world_target_id":sorted(dominated)[0],
            "terminal_false_world_target_id":sorted(residual)[0],
            "same_brain_side_information":True,
            "meaning":"WITHOUT_ADDITIONAL_TARGET_INFORMATION_THESE_TWO_TARGET_WORLDS_REMAIN_POSSIBLE_BUT_HAVE_DIFFERENT_TERMINAL_DOMINANCE_TRUTH",
            **out,
        }
    return {
        "countermodel_exists":False,
        "positive_certificate_impossible_on_current_uncertainty_set":True,
        "reason":"EVERY_CURRENTLY_POSSIBLE_TARGET_LAW_IS_UNDOMINATED",
        **out,
    }


def all_laws_top_element_certificate(
    brain_law: Mapping[str,float],
    admissible_laws: Sequence[Mapping[str,Any]],
    *,
    evaluators: Sequence[Mapping[str,float]],
    hard_constraints: Sequence[Mapping[str,Any]] = (),
) -> dict[str,Any]:
    out=target_law_residual(
        brain_law,
        admissible_laws,
        evaluators=evaluators,
        hard_constraints=hard_constraints,
    )
    return {
        **out,
        "brain_is_top_over_declared_admissible_law_space":out["undominated_residual_count"]==0,
        "target_law_information_required_if_target_is_proved_inside_declared_space":out["undominated_residual_count"]!=0,
    }
