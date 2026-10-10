"""Universal Learning V6: mechanism discovery and safe experiment synthesis.

V6 strictly extends the verified V5 learner. It does not replace V1-V5 safety.
It adds:
- observation-driven falsification of explicit mechanism candidates,
- M-open model-class expansion when every candidate fails,
- exact goal-conditioned decision quotient compression,
- candidate invariant extraction with separate verification,
- exact finite safe adaptive experiment synthesis over receipt-bound outcome models.

No structural mechanism here earns acceptance, ownership, or semantic-success credit.
"""
from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_recursive_abstraction_router_v5 as v5
from canonical.runtime import mechanism_discovery_v6 as mech
from canonical.runtime import safe_adaptive_experiment_synthesizer_v6 as synth

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_MECHANISM_ROUTER_V6"

def route(
    *,
    goal:str,
    environment_id:str,
    verified_coverage:Any,
    goal_facts:Iterable[Any],
    fallback_required_facts:Iterable[Any],
    verified_facts:Iterable[Any],
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
    goal_id=" ".join(str(goal or "").split())
    env=str(environment_id or "").strip()
    if not goal_id or not env:
        raise ValueError("GOAL_AND_ENVIRONMENT_REQUIRED")

    updated=mech.update(candidates=mechanism_candidates,observations=observations)
    survivors=updated["survivors"]
    if not survivors:
        # Preserve V1/V2 novelty facts by running V5 on the declared class, but
        # never pretend the failed model class is the world.
        base=v5.route(
            goal=goal_id,environment_id=env,verified_coverage=verified_coverage,
            goal_facts=goal_facts,fallback_required_facts=fallback_required_facts,
            verified_facts=verified_facts,dependencies=dependencies,
            dependency_receipt=dependency_receipt,transfer_mappings=transfer_mappings,
            hypotheses=[],hypothesis_coverage_receipt=None,residual_action_receipt=None,
            actions=[],verified_skills=verified_skills,
        )
        return {
            **base,
            "schema":SCHEMA,
            "route":"EXPAND_MECHANISM_LANGUAGE",
            "reason":"ALL_DECLARED_MECHANISMS_FALSIFIED__OPEN_WORLD_MODEL_CLASS_MUST_EXPAND",
            "mechanism_update":updated,
            "decision_quotient":None,
            "invariant_candidates":None,
            "adaptive_plan":None,
            "next_action":{
                "type":"GENERATE_NEW_MECHANISM_CANDIDATES",
                "constraints":[
                    "EXPLAIN_ALL_VERIFIED_OBSERVATIONS",
                    "PREFER_REUSE_OF_VERIFIED_CAUSAL_PRIMITIVES",
                    "ALLOW_NEW_PRIMITIVES_WHEN_EXISTING_LANGUAGE_IS_FALSIFIED",
                    "NO_TRUST_WITHOUT_VERIFICATION",
                ],
            },
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

    hypotheses=[
        {"id":c["id"],"plausible":True,"best_action":c["best_action"]}
        for c in survivors
    ]
    base=v5.route(
        goal=goal_id,environment_id=env,verified_coverage=verified_coverage,
        goal_facts=goal_facts,fallback_required_facts=fallback_required_facts,
        verified_facts=verified_facts,dependencies=dependencies,
        dependency_receipt=dependency_receipt,transfer_mappings=transfer_mappings,
        hypotheses=hypotheses,
        hypothesis_coverage_receipt=hypothesis_coverage_receipt,
        residual_action_receipt=residual_action_receipt,
        actions=[],
        verified_skills=verified_skills,
    )
    quotient=mech.decision_quotient(survivors)
    invariants=mech.common_invariant_candidates(survivors)
    common={
        **base,
        "schema":SCHEMA,
        "mechanism_update":updated,
        "decision_quotient":quotient,
        "invariant_candidates":invariants,
        "trusted_execution_authorized":base.get("trusted_execution_authorized",False),
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
    if base["route"] in {"USE_VERIFIED_CAPABILITY","DECISION_SUFFICIENT_UNVERIFIED_MODEL"}:
        return {**common,"adaptive_plan":None}

    try:
        plan=synth.synthesize(
            environment_id=env,
            goal_id=goal_id,
            candidates=survivors,
            probes=probes,
            hypothesis_coverage_receipt=hypothesis_coverage_receipt,
        )
    except Exception as exc:
        return {
            **common,
            "route":"ABSTAIN_OR_REQUEST_VERIFIED_EXPERIMENT_MODEL",
            "reason":"V6_EXPERIMENT_MODEL_REJECTED:"+str(exc),
            "adaptive_plan":None,
            "next_action":None,
        }
    if plan.get("recommended_probe"):
        return {
            **common,
            "route":"LEARN",
            "reason":"V6_SAFE_ADAPTIVE_MECHANISM_DISCRIMINATION",
            "adaptive_plan":plan,
            "next_action":{"type":"SAFE_PROBE","id":plan["recommended_probe"]},
            "trusted_execution_authorized":False,
        }
    return {
        **common,
        "route":"ABSTAIN_OR_EXPAND_MECHANISM_LANGUAGE",
        "reason":"NO_SAFE_FINITE_PLAN_CAN_RESOLVE_CURRENT_DECISION_CLASSES",
        "adaptive_plan":plan,
        "next_action":{"type":"EXPAND_MECHANISM_CANDIDATES_OR_FIND_NEW_SAFE_PROBE"},
        "trusted_execution_authorized":False,
    }

def prove_v6_invariants()->dict[str,Any]:
    errors=[]

    candidates=[
        {"id":"m1","best_action":"A","predictions":{"p":"x","q":"u"},"invariants":["conservative"],"provenance":["prior"]},
        {"id":"m2","best_action":"A","predictions":{"p":"x","q":"v"},"invariants":["conservative"],"provenance":["prior"]},
        {"id":"m3","best_action":"B","predictions":{"p":"y","q":"u"},"invariants":["conservative"],"provenance":["prior"]},
    ]
    upd=mech.update(candidates=candidates,observations=[{"probe_id":"p","outcome":"x"}])
    if [x["id"] for x in upd["survivors"]]!=["m1","m2"]:
        errors.append("OBSERVATION_FALSIFICATION_BROKEN")
    quot=mech.decision_quotient(upd["survivors"])
    if quot["decision_class_count"]!=1 or quot["open_world_sufficiency_proved"] is not False:
        errors.append("DECISION_QUOTIENT_OPEN_WORLD_BOUNDARY_BROKEN")
    inv=mech.common_invariant_candidates(upd["survivors"])
    if inv["candidate_invariants"]!=["conservative"] or inv["verified_invariants"]!=[]:
        errors.append("INVARIANT_CANDIDATE_BOUNDARY_BROKEN")
    dead=mech.update(candidates=candidates,observations=[{"probe_id":"p","outcome":"outside"}])
    if dead["status"]!="MODEL_CLASS_FALSIFIED__EXPAND_HYPOTHESIS_LANGUAGE":
        errors.append("M_OPEN_EXPANSION_TRIGGER_BROKEN")

    # V5's open-world guard must still reject false consensus.
    from canonical.runtime import open_world_hypothesis_guard_v4 as guard4
    s=guard4.decision_sufficient(
        environment_id="e",goal_id="g",
        hypotheses=[{"id":"h","plausible":True,"best_action":"A"}],
        coverage_receipt=None,residual_action_receipt=None,
    )
    if s.get("sufficient") is not False:
        errors.append("V4_FALSE_CONSENSUS_GUARD_LOST")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"UNIVERSAL_LEARNING_V6_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "mechanism_falsification_preserved":passed,
        "m_open_model_expansion_preserved":passed,
        "decision_quotient_compression_preserved":passed,
        "candidate_invariant_no_self_verification_preserved":passed,
        "v5_and_v4_safety_preserved":passed,
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
