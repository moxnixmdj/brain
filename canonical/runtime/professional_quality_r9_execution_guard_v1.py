"""Claim-bound R9 temporal/deployment execution enforcement guard V1.

This layer enforces already-bound conservative censoring plus detected temporal
defeaters. It does not prove defeater-detection completeness, semantic closure,
whole-leaf property truth, root closure, quality, acceptance, promotion, or
terminal authority.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

CLAIM_ID="edfe88a8e01f6b62a018891a098df872d9307addd2336b6e67d140084c37ed4f"
LEAF_ID="PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION"
ROOT_ID="R9_TEMPORAL_DEPLOYMENT"
CENSORING_SCHEMA="PROJECT_BRAIN_TB_SCIENCE_CONSERVATIVE_CENSORING_REDUCER_V1"

KNOWN_R9_DEFEATERS=frozenset({
 "C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
 "C31_EDIT_SEQUENCE_INTERACTION",
 "C40_CARRYOVER_LEARNING",
 "C41_HORIZON_REVERSAL",
 "C42_SELECTIVE_OUTCOME_CENSORING",
 "C43_RARE_UNSEEN_FAILURE",
 "C44_TAIL_RISK_AVERAGE_MASKING",
 "C45_DEPLOYMENT_SUPPORT_SHIFT",
 "C46_PERFORMATIVE_SELF_CONFIRMATION",
 "C47_BAD_EQUILIBRIUM_PATH",
 "C57_EVALUATION_AWARE_BEHAVIOR",
 "C73_BASE_RATE_PRECISION_LAUNDERING",
 "C75_STALE_CERT_AFTER_DEPENDENCY_CHANGE",
})

NEAR_MISS_TO_TRIGGER={
 "horizon_or_time_transport_gap":"POPULATION_CONTEXT_OPERATOR_OR_TIME_TRANSPORT_GAP",
 "material_invariance_failure":"MATERIAL_INVARIANCE_FAILURE",
 "adaptive_contamination_or_evaluation_awareness":"ADAPTIVE_CONTAMINATION_OR_HOLDOUT_EXPOSURE",
 "high_consequence_tail_or_veto":"HIGH_CONSEQUENCE_OR_VETO_DIMENSION",
}

def _base(status:str,*,passed:bool)->dict[str,Any]:
    return {
      "schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_EXECUTION_GUARD_V1",
      "status":status,"pass":passed,"leaf_id":LEAF_ID,"root_id":ROOT_ID,
      "claim_id":CLAIM_ID,"detection_completeness_proved":False,
      "whole_leaf_property_truth_proved":False,
      "semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {**_base("FAIL_CLOSED",passed=False),"reason":reason,**extra}

def _catalog_ids(catalog:Mapping[str,Any])->set[str]:
    rows=catalog.get("challenges")
    if not isinstance(rows,list):
        rows=catalog.get("defeaters")
    if not isinstance(rows,list):
        return set()
    out=set()
    for row in rows:
        if not isinstance(row,Mapping): continue
        roots=row.get("root_ids")
        if ROOT_ID in (roots if isinstance(roots,list) else []):
            did=row.get("id")
            if isinstance(did,str) and did: out.add(did)
    return out

def _profile_triggers(profile:Mapping[str,Any])->set[str]:
    vals=profile.get("escalation_triggers")
    return {x for x in (vals or []) if isinstance(x,str) and x}

def _censoring_valid(v:Mapping[str,Any])->bool:
    if v.get("schema")!=CENSORING_SCHEMA: return False
    if v.get("total_slots")!=210 or v.get("required_successes")!=124: return False
    if v.get("unobserved_slots_count_as_zero_on_finalization") is not True: return False
    successes=v.get("successes")
    if isinstance(successes,bool) or not isinstance(successes,int) or not (0<=successes<=210): return False
    rate=v.get("lower_bound_rate")
    if isinstance(rate,bool) or not isinstance(rate,(int,float)): return False
    if abs(float(rate)-successes/210.0)>1e-12: return False
    status=v.get("status")
    pass_locked=v.get("pass_locked")
    fail_locked=v.get("fail_locked")
    if not isinstance(pass_locked,bool) or not isinstance(fail_locked,bool): return False
    if pass_locked and fail_locked: return False
    if status=="PASS_LOCK" and not pass_locked: return False
    if status=="FAIL_LOCK" and not fail_locked: return False
    if status=="OPEN" and (pass_locked or fail_locked): return False
    if status not in {"PASS_LOCK","FAIL_LOCK","OPEN"}: return False
    return True

def evaluate(
 *,
 claim_id:str,
 censoring_verdict:Mapping[str,Any],
 execution_profile:Mapping[str,Any],
 defeater_catalog:Mapping[str,Any],
 detected_defeater_ids:Sequence[str]=(),
 near_miss_signals:Mapping[str,bool]|None=None,
 unmapped_material_false_certification_defeater:bool=False,
 dependency_fresh:bool=True,
)->dict[str,Any]:
    if claim_id!=CLAIM_ID:
        return _fail("CLAIM_ID_MISMATCH")
    observed=_catalog_ids(defeater_catalog)
    if observed!=set(KNOWN_R9_DEFEATERS):
        return _fail("R9_DEFEATER_CATALOG_DRIFT",
                     expected_ids=sorted(KNOWN_R9_DEFEATERS),
                     observed_ids=sorted(observed))
    required=set(NEAR_MISS_TO_TRIGGER.values())|{"UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"}
    missing=sorted(required-_profile_triggers(execution_profile))
    if missing:
        return _fail("PROFILE_ESCALATION_TRIGGER_MISSING",missing_triggers=missing)
    if not isinstance(censoring_verdict,Mapping) or not _censoring_valid(censoring_verdict):
        return _fail("CENSORING_INVARIANT_DRIFT")
    if dependency_fresh is not True:
        return {**_base("ABSTAIN_OR_ESCALATE__R9_STALE_DEPENDENCY",passed=False),
                "ordinary_certificate_path_allowed":False}
    detected=[x for x in detected_defeater_ids if isinstance(x,str)]
    unknown=sorted(set(detected)-set(KNOWN_R9_DEFEATERS))
    if unknown:
        return {**_base("ESCALATE__UNMAPPED_DETECTED_DEFEATER",passed=False),
                "unknown_detected_defeater_ids":unknown,
                "required_trigger":"UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
                "ordinary_certificate_path_allowed":False}
    if detected:
        return {**_base("ABSTAIN_OR_ESCALATE__KNOWN_R9_DEFEATER_ACTIVE",passed=False),
                "detected_defeater_ids":sorted(set(detected)),
                "ordinary_certificate_path_allowed":False}
    if unmapped_material_false_certification_defeater:
        return {**_base("ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",passed=False),
                "required_trigger":"UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
                "ordinary_certificate_path_allowed":False}
    active=[]
    for signal,trigger in NEAR_MISS_TO_TRIGGER.items():
        if (near_miss_signals or {}).get(signal) is True: active.append(trigger)
    if active:
        return {**_base("ESCALATE__R9_NEAR_MISS_TRIGGER",passed=False),
                "active_escalation_triggers":sorted(active),
                "ordinary_certificate_path_allowed":False}
    if censoring_verdict.get("status")!="PASS_LOCK" or censoring_verdict.get("pass_locked") is not True:
        return {**_base("ABSTAIN_OR_ESCALATE__R9_CENSORING_NOT_PASS_LOCK",passed=False),
                "censoring_status":censoring_verdict.get("status"),
                "ordinary_certificate_path_allowed":False}
    return {**_base("PASS__R9_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION",passed=True),
            "ordinary_certificate_path_allowed":True,
            "detected_defeater_ids":[],
            "active_escalation_triggers":[],
            "property_scope":"DETECTION_TO_ENFORCEMENT_PLUS_CONSERVATIVE_CENSORING_ONLY__DEFEATER_DETECTION_COMPLETENESS_SEPARATE"}
