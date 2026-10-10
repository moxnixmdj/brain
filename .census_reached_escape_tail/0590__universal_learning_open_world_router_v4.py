"""Universal Learning V4: goal-minimal, open-world guarded decision routing."""
from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_contract_v1 as v1
from canonical.runtime import universal_active_transfer_learner_v2 as v2
from canonical.runtime import structural_transfer_v3 as transfer
from canonical.runtime import goal_dependency_delta_v4 as delta4
from canonical.runtime import open_world_hypothesis_guard_v4 as guard4

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_OPEN_WORLD_ROUTER_V4"

def route(*,goal:str,environment_id:str,verified_coverage:Any,goal_facts:Iterable[Any],fallback_required_facts:Iterable[Any],verified_facts:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]],dependency_receipt:Mapping[str,Any]|None,transfer_mappings:Sequence[Mapping[str,Any]],hypotheses:Sequence[Mapping[str,Any]],hypothesis_coverage_receipt:Mapping[str,Any]|None,residual_action_receipt:Mapping[str,Any]|None,actions:Sequence[Mapping[str,Any]])->dict[str,Any]:
    goal_id=" ".join(str(goal or "").split()); env=str(environment_id or "").strip()
    if not goal_id or not env:
        raise ValueError("GOAL_AND_ENVIRONMENT_REQUIRED")
    base=v1.route_input(verified_coverage=verified_coverage)
    coverage=transfer.apply(verified_facts=verified_facts,mappings=transfer_mappings)
    if dependency_receipt is not None:
        novelty=delta4.minimum_goal_delta(environment_id=env,goal_id=goal_id,goals=goal_facts,verified_facts=coverage["verified_facts"],dependencies=dependencies,dependency_receipt=dependency_receipt)
        novelty_kind="PROVED_GOAL_DEPENDENCY_CONE"
    else:
        novelty=v2.minimum_novelty_delta(required_facts=fallback_required_facts,verified_facts=coverage["verified_facts"])
        novelty_kind="CONSERVATIVE_FLAT_FALLBACK"
    common={
        "schema":SCHEMA,
        "novelty_delta":novelty,
        "novelty_delta_kind":novelty_kind,
        "transfer_coverage":coverage,
        "trusted_execution_authorized":False,
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
    if base["route"]=="USE_VERIFIED_CAPABILITY" and not novelty["missing"]:
        return {**common,"route":"USE_VERIFIED_CAPABILITY","trusted_execution_authorized":True,"reason":"VERIFIED_COVERAGE_AND_ZERO_GOAL_RELEVANT_NOVELTY","recommended_action":None,"next_action":None}
    suff=guard4.decision_sufficient(environment_id=env,goal_id=goal_id,hypotheses=hypotheses,coverage_receipt=hypothesis_coverage_receipt,residual_action_receipt=residual_action_receipt)
    if suff["sufficient"] and suff.get("open_world_safe") is True:
        return {**common,"route":"DECISION_SUFFICIENT_UNVERIFIED_MODEL","reason":suff["reason"],"decision_sufficiency":suff,"recommended_action":suff["action"],"next_action":None}
    ranked=guard4.robust_rank(environment_id=env,goal_id=goal_id,hypotheses=hypotheses,actions=actions)
    if ranked["ranked"]:
        return {**common,"route":"LEARN","reason":"OPEN_WORLD_SAFE_MINIMAX_DISCRIMINATOR_AVAILABLE","decision_sufficiency":suff,"recommended_action":None,"next_action":ranked["ranked"][0],"ranked_discriminators":ranked["ranked"],"rejected_discriminators":ranked["rejected"]}
    return {**common,"route":"ABSTAIN_OR_REQUEST_DISCRIMINATOR","reason":"NO_OPEN_WORLD_SAFE_DECISION_SUFFICIENCY_OR_POSITIVE_MINIMAX_PROBE","decision_sufficiency":suff,"recommended_action":None,"next_action":None,"rejected_discriminators":ranked["rejected"]}
