"""Universal Learning V5: V4 safety plus superset compression and recursive abstraction."""
from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_contract_v1 as v1
from canonical.runtime import universal_active_transfer_learner_v2 as v2
from canonical.runtime import structural_transfer_v3 as transfer
from canonical.runtime import open_world_hypothesis_guard_v4 as guard4
from canonical.runtime import dependency_superset_delta_v5 as delta5
from canonical.runtime import recursive_abstraction_v5 as abs5
from canonical.runtime import compounding_probe_rank_v5 as rank5

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_RECURSIVE_ABSTRACTION_ROUTER_V5"

def route(*,goal:str,environment_id:str,verified_coverage:Any,goal_facts:Iterable[Any],fallback_required_facts:Iterable[Any],verified_facts:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]],dependency_receipt:Mapping[str,Any]|None,transfer_mappings:Sequence[Mapping[str,Any]],hypotheses:Sequence[Mapping[str,Any]],hypothesis_coverage_receipt:Mapping[str,Any]|None,residual_action_receipt:Mapping[str,Any]|None,actions:Sequence[Mapping[str,Any]],verified_skills:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
    goal_id=" ".join(str(goal or "").split()); env=str(environment_id or "").strip()
    if not goal_id or not env:
        raise ValueError("GOAL_AND_ENVIRONMENT_REQUIRED")
    base=v1.route_input(verified_coverage=verified_coverage)
    coverage=transfer.apply(verified_facts=verified_facts,mappings=transfer_mappings)
    if dependency_receipt is not None:
        novelty=delta5.goal_delta_upper_bound(environment_id=env,goal_id=goal_id,goals=goal_facts,verified_facts=coverage["verified_facts"],dependencies=dependencies,dependency_receipt=dependency_receipt)
        novelty_kind="EXACT_GOAL_DEPENDENCY_CONE" if novelty["scope_relation"]=="EXACT" else "PROVEN_DEPENDENCY_SUPERSET"
    else:
        novelty=v2.minimum_novelty_delta(required_facts=fallback_required_facts,verified_facts=coverage["verified_facts"])
        novelty_kind="CONSERVATIVE_FLAT_FALLBACK"
    abstraction_candidate=None
    abstraction_candidate_status="INSUFFICIENT_VERIFIED_SKILLS_FOR_ABSTRACTION"
    if len(verified_skills)>=2:
        try:
            abstraction_candidate=abs5.induce_candidate(verified_skills)
            abstraction_candidate_status="CANDIDATE_EMITTED"
        except abs5.RecursiveAbstractionError as exc:
            if str(exc)!="NO_COMMON_VERIFIED_STRUCTURE":
                raise
            abstraction_candidate_status="NO_COMMON_VERIFIED_STRUCTURE"
    common={
        "schema":SCHEMA,
        "novelty_delta":novelty,
        "novelty_delta_kind":novelty_kind,
        "transfer_coverage":coverage,
        "abstraction_candidate":abstraction_candidate,
        "abstraction_candidate_status":abstraction_candidate_status,
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
    ranked=rank5.rank(environment_id=env,goal_id=goal_id,hypotheses=hypotheses,actions=actions)
    if ranked["ranked"]:
        return {**common,"route":"LEARN","reason":"OPEN_WORLD_SAFE_MINIMAX_DISCRIMINATOR_AVAILABLE__COMPOUNDING_TIEBREAK","decision_sufficiency":suff,"recommended_action":None,"next_action":ranked["ranked"][0],"ranked_discriminators":ranked["ranked"],"rejected_discriminators":ranked["rejected"]}
    return {**common,"route":"ABSTAIN_OR_REQUEST_DISCRIMINATOR","reason":"NO_OPEN_WORLD_SAFE_DECISION_SUFFICIENCY_OR_ADMISSIBLE_POSITIVE_MINIMAX_PROBE","decision_sufficiency":suff,"recommended_action":None,"next_action":None,"rejected_discriminators":ranked["rejected"]}

def prove_v5_invariants()->dict[str,Any]:
    errors=[]
    # Preserve V4 open-world false-consensus guard.
    suff=guard4.decision_sufficient(environment_id="e",goal_id="g",hypotheses=[{"id":"h","plausible":True,"best_action":"a"}],coverage_receipt=None,residual_action_receipt=None)
    if suff.get("sufficient") is not False:
        errors.append("V4_OPEN_WORLD_FALSE_CONSENSUS_GUARD_LOST")

    graph={"goal":["needed","extra"]}
    receipt={
        "receipt_id":"d","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "environment_id":"e","goal_id":"g","scope_relation":"PROVEN_SUPERSET",
        "all_true_decision_relevant_dependencies_contained":True,
        "dependency_graph_sha256":delta5.dependency_digest(goals=["goal"],dependencies=graph),
    }
    delta=delta5.goal_delta_upper_bound(environment_id="e",goal_id="g",goals=["goal"],verified_facts=[],dependencies=graph,dependency_receipt=receipt)
    if not delta.get("sound_upper_bound_on_required_novelty") or delta.get("minimality_proved"):
        errors.append("DEPENDENCY_SUPERSET_SOUNDNESS_BROKEN")

    def sk(sid,sig):
        dg=abs5.signature_digest(sig)
        return {"skill_id":sid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","canonical_signature":sig,
                "canonicalization_receipt":{"receipt_id":"r-"+sid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","skill_id":sid,"signature_sha256":dg,"mapping_basis":"FORMAL_REDUCTION"}}
    cand=abs5.induce_candidate([sk("a",["x","y"]),sk("b",["x","z"])])
    if cand.get("verified_abstraction") is not False or cand.get("promotion_authorized") is not False:
        errors.append("ABSTRACTION_SELF_CERTIFICATION_ALLOWED")

    env,goal="e","g"
    def sr(aid):
        return {"receipt_id":"s-"+aid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","safe_under_all_admissible_worlds":True,"environment_id":env,"goal_id":goal,"action_id":aid}
    ranked=rank5.rank(environment_id=env,goal_id=goal,hypotheses=[
        {"id":"h1","plausible":True,"best_action":"a"},{"id":"h2","plausible":True,"best_action":"b"},{"id":"h3","plausible":True,"best_action":"c"}],
        actions=[
            {"id":"primary","safety_receipt":sr("primary"),"outcome_by_hypothesis":{"h1":"1","h2":"2","h3":"3"},"time":2,"cost":0,"risk":0,"incremental_spend_usd_ub":0,"future_transfer_lcb":0,"proof_value_lcb":0,"future_burden_ub":10},
            {"id":"flashy","safety_receipt":sr("flashy"),"outcome_by_hypothesis":{"h1":"1","h2":"1","h3":"2"},"time":1,"cost":0,"risk":0,"incremental_spend_usd_ub":0,"future_transfer_lcb":100,"proof_value_lcb":100,"future_burden_ub":0},
        ])
    if not ranked["ranked"] or ranked["ranked"][0]["id"]!="primary":
        errors.append("MINIMAX_PRIMARY_ORDER_NOT_PRESERVED")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"UNIVERSAL_LEARNING_V5_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "v4_open_world_guard_preserved":passed,
        "dependency_superset_pruning_sound":passed,
        "abstraction_induction_candidate_only":passed,
        "minimax_primary_order_preserved":passed,
        "semantic_success_rate_proved":False,
        "unknown_domain_acceptance_proved":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "incremental_spend_usd":0,
    }
