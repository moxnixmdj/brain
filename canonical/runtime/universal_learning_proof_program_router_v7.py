"""Universal Learning V7 proof-first executable-learning router.

V7 strictly extends V6:
- verified deduction is exhausted before empirical information acquisition,
- only the irreducible empirical frontier is passed to the V6 learner,
- repeated independently verified traces may induce executable skill candidates,
- generated candidates remain untrusted until independent behavior verification.

No V7 structure earns terminal acceptance, ownership, or fresh-reality authority.
"""
from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import deductive_closure_v7 as dc
from canonical.runtime import executable_skill_program_v7 as sp
from canonical.runtime import universal_learning_mechanism_router_v6 as v6

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_PROOF_PROGRAM_ROUTER_V7"

def route(
    *,
    goal:str,
    environment_id:str,
    scope_id:str,
    required_facts:Iterable[Any],
    verified_fact_evidence:Sequence[Mapping[str,Any]],
    verified_rules:Sequence[Mapping[str,Any]],
    learning_episodes:Sequence[Mapping[str,Any]],
    verified_coverage:Any,
    goal_facts:Iterable[Any],
    fallback_required_facts:Iterable[Any],
    dependencies:Mapping[Any,Iterable[Any]],
    dependency_receipt:Mapping[str,Any]|None,
    transfer_mappings:Sequence[Mapping[str,Any]],
    mechanism_candidates:Sequence[Mapping[str,Any]],
    observations:Sequence[Mapping[str,Any]],
    hypothesis_coverage_receipt:Mapping[str,Any]|None,
    residual_action_receipt:Mapping[str,Any]|None,
    probes:Sequence[Mapping[str,Any]],
    verified_skills:Sequence[Mapping[str,Any]]=(),
)->dict[str,Any]:
    closure=dc.derive(
        scope_id=scope_id,
        verified_facts=verified_fact_evidence,
        verified_rules=verified_rules,
        required_facts=required_facts,
    )

    program_candidate=None
    program_status="INSUFFICIENT_VERIFIED_EPISODES"
    if len(learning_episodes)>=2:
        try:
            program_candidate=sp.induce_candidate(learning_episodes)
            program_status=program_candidate["status"]
        except Exception as exc:
            program_status="NO_SOUND_EXECUTABLE_PROGRAM_CANDIDATE:"+str(exc)

    common={
        "schema":SCHEMA,
        "deductive_closure":closure,
        "executable_skill_candidate":program_candidate,
        "executable_skill_candidate_status":program_status,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }

    if closure["required_facts"] and not closure["empirical_frontier"]:
        return {
            **common,
            "route":"PROOF_SUFFICIENT_NO_EMPIRICAL_LEARNING",
            "reason":"ALL_DECLARED_DECISION_RELEVANT_FACTS_DERIVED_FROM_INDEPENDENTLY_VERIFIED_FACTS_AND_RULES",
            "empirical_information_action_authorized":False,
            "v6_result":None,
            "next_action":{"type":"USE_PROOF_CLOSURE_OR_EXECUTE_SEPARATELY_VERIFIED_CAPABILITY"},
            "trusted_execution_authorized":False,
        }

    base=v6.route(
        goal=goal,
        environment_id=environment_id,
        verified_coverage=verified_coverage,
        goal_facts=goal_facts,
        fallback_required_facts=fallback_required_facts,
        verified_facts=closure["closure"],
        dependencies=dependencies,
        dependency_receipt=dependency_receipt,
        transfer_mappings=transfer_mappings,
        mechanism_candidates=mechanism_candidates,
        observations=observations,
        hypothesis_coverage_receipt=hypothesis_coverage_receipt,
        residual_action_receipt=residual_action_receipt,
        probes=probes,
        verified_skills=verified_skills,
    )
    return {
        **common,
        "route":base["route"],
        "reason":"V7_DEDUCTION_EXHAUSTED__V6_RECEIVES_ONLY_REMAINING_EMPIRICAL_FRONTIER",
        "empirical_information_action_authorized":bool(closure["empirical_frontier"]),
        "v6_result":base,
        "next_action":base.get("next_action"),
        "trusted_execution_authorized":base.get("trusted_execution_authorized",False),
    }

def prove_v7_invariants()->dict[str,Any]:
    errors=[]
    scope="s"
    fact="a"
    fsha=dc.fact_digest(scope_id=scope,fact=fact)
    facts=[{
        "fact":fact,
        "verification_receipt":{
            "receipt_id":"fr","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","scope_id":scope,"fact":fact,"fact_sha256":fsha,
        },
    }]
    rsha=dc.rule_digest(scope_id=scope,rule_id="r1",premises=["a"],conclusion="b")
    rules=[{
        "id":"r1","premises":["a"],"conclusion":"b",
        "verification_receipt":{
            "receipt_id":"rr","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","sound_on_claimed_scope":True,
            "scope_id":scope,"rule_id":"r1","rule_sha256":rsha,
        },
    }]
    out=dc.derive(scope_id=scope,verified_facts=facts,verified_rules=rules,required_facts=["b"])
    if out["empirical_action_required"] is not False or "b" not in out["closure"]:
        errors.append("DEDUCTION_BEFORE_OBSERVATION_BROKEN")

    steps=[{"op":"inspect","inputs":["target"],"outputs":["model"]},{"op":"verify","inputs":["model"],"outputs":["proof"]}]
    pd=sp.program_digest(steps=steps,preconditions=["target-present"],postconditions=["proof"],invalidators=["target-changed"])
    def ep(eid,scope_id):
        return {
            "episode_id":eid,"scope_id":scope_id,"steps":steps,
            "preconditions":["target-present"],"postconditions":["proof"],"invalidators":["target-changed"],
            "verification_receipt":{
                "receipt_id":"vr-"+eid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","behavior_verified":True,
                "episode_id":eid,"scope_id":scope_id,"program_sha256":pd,
            },
        }
    cand=sp.induce_candidate([ep("e1","x"),ep("e2","y")])
    if cand["verified_skill"] is not False or cand["reuse_authorized"] is not False:
        errors.append("PROGRAM_CANDIDATE_SELF_TRUST_BROKEN")

    v6inv=v6.prove_v6_invariants()
    if v6inv.get("pass") is not True:
        errors.append("V6_BASE_INVARIANTS_NOT_PRESERVED")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"UNIVERSAL_LEARNING_V7_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "deduction_before_observation_preserved":passed,
        "executable_program_candidate_no_self_verification_preserved":passed,
        "v6_base_preserved":passed,
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
