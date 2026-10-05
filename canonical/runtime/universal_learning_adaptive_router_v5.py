"""Universal Learning V5 verified adaptive experiment router."""
from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_open_world_router_v4 as v4
from canonical.runtime import adaptive_experiment_planner_v5 as planner

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_ADAPTIVE_ROUTER_V5"

def route(*,goal:str,environment_id:str,verified_coverage:Any,goal_facts:Iterable[Any],fallback_required_facts:Iterable[Any],verified_facts:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]],dependency_receipt:Mapping[str,Any]|None,transfer_mappings:Sequence[Mapping[str,Any]],hypotheses:Sequence[Mapping[str,Any]],hypothesis_coverage_receipt:Mapping[str,Any]|None,residual_action_receipt:Mapping[str,Any]|None,probes:Sequence[Mapping[str,Any]])->dict[str,Any]:
    base=v4.route(
        goal=goal,environment_id=environment_id,verified_coverage=verified_coverage,
        goal_facts=goal_facts,fallback_required_facts=fallback_required_facts,
        verified_facts=verified_facts,dependencies=dependencies,dependency_receipt=dependency_receipt,
        transfer_mappings=transfer_mappings,hypotheses=hypotheses,
        hypothesis_coverage_receipt=hypothesis_coverage_receipt,
        residual_action_receipt=residual_action_receipt,actions=[],
    )
    common={**base,"schema":SCHEMA,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
    if base["route"] in {"USE_VERIFIED_CAPABILITY","DECISION_SUFFICIENT_UNVERIFIED_MODEL"}:
        return common
    if hypothesis_coverage_receipt is None:
        return {**common,"route":"ABSTAIN_OR_REQUEST_VERIFIED_MODEL","reason":"ADAPTIVE_PLANNING_REQUIRES_CLOSED_DECISION_RELEVANT_HYPOTHESIS_SPACE","next_action":None}
    try:
        p=planner.plan(environment_id=environment_id,goal_id=" ".join(str(goal or "").split()),hypotheses=hypotheses,hypothesis_coverage_receipt=hypothesis_coverage_receipt,probes=probes)
    except Exception as exc:
        return {**common,"route":"ABSTAIN_OR_REQUEST_VERIFIED_MODEL","reason":"VERIFIED_ADAPTIVE_PLAN_INPUT_REJECTED:"+str(exc),"next_action":None}
    if p["status"]!="VERIFIED_MINIMUM_WORST_CASE_ADAPTIVE_PLAN":
        return {**common,"route":"ABSTAIN_OR_REQUEST_DISCRIMINATOR","reason":"NO_VERIFIED_ADAPTIVE_RESOLUTION_PLAN","adaptive_plan":p,"next_action":None}
    return {**common,"route":"LEARN","reason":"VERIFIED_MINIMUM_WORST_CASE_ADAPTIVE_EXPERIMENT_PLAN","adaptive_plan":p,"next_action":{"id":p["recommended_probe"]}}
