"""Lift chronology-safe postwave atomic ceiling evidence into a family-level candidate witness.

This compiler does not promote anything. It emits a standard candidate witness for
the existing acceptance_proof_transmuter only when:
- the frozen atomic registry declares a lossless decomposition;
- the family maps to exactly one residual behavioral contract;
- the terminal family and that residual contract passed behaviorally;
- every family predicate other than the target is already independently/objectively
  PROVED with complete scope; and
- the target predicate has a chronology-safe immutable postwave theoretical-ceiling
  candidate from postwave_evidence_reconciler_v1.

The result remains verified=False / independent=False until an external verifier
binds the exact source blobs.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_POSTWAVE_ATOMIC_FAMILY_WITNESS_LIFTER_V1"
LOSSLESS_RULE="REGISTRY_IS_A_LOSSLESS_DECOMPOSITION_OF_FROZEN_ACCEPTANCE_RULES__NOT_A_WEAKENING"
ALL_RULE="ALL_PREDICATES_FOR_A_FAMILY_MUST_BE_PROVED_BEFORE_FAMILY_PROMOTION"


def _fail(*errors:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "pass":False,
        "errors":sorted(set(errors)),
        "candidate_witness":None,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }


def _unique_protocol(protocols:Mapping[str,Any],family:str)->Mapping[str,Any]|None:
    rows=protocols.get("protocols")
    if not isinstance(rows,list):
        return None
    found=[r for r in rows if isinstance(r,Mapping) and r.get("family")==family]
    return found[0] if len(found)==1 else None


def evaluate(
    *,
    family:str,
    target_predicate:str,
    reconciliation:Mapping[str,Any],
    registry:Mapping[str,Any],
    evidence:Mapping[str,Any],
    behavioral_registry:Mapping[str,Any],
    behavioral_reduction:Mapping[str,Any],
    protocols:Mapping[str,Any],
)->dict[str,Any]:
    errors:list[str]=[]

    if reconciliation.get("status")!="PASS":
        errors.append("RECONCILIATION_NOT_PASS")

    rules=registry.get("rules")
    if not isinstance(rules,list) or LOSSLESS_RULE not in rules:
        errors.append("LOSSLESS_ATOMIC_DECOMPOSITION_NOT_BOUND")
    if not isinstance(rules,list) or ALL_RULE not in rules:
        errors.append("ALL_PREDICATES_PROMOTION_RULE_NOT_BOUND")

    prows=registry.get("predicates")
    if not isinstance(prows,list):
        prows=[]
        errors.append("PREDICATES_NOT_LIST")
    family_predicates=[
        r for r in prows
        if isinstance(r,Mapping) and r.get("family")==family
    ]
    if not family_predicates:
        errors.append("FAMILY_ATOMIC_PREDICATES_MISSING")
    ids=[
        r.get("id") for r in family_predicates
        if isinstance(r.get("id"),str)
    ]
    if len(ids)!=len(family_predicates) or len(set(ids))!=len(ids):
        errors.append("FAMILY_ATOMIC_PREDICATE_IDS_INVALID")
    target_rows=[r for r in family_predicates if r.get("id")==target_predicate]
    if len(target_rows)!=1:
        errors.append("TARGET_PREDICATE_NOT_UNIQUE_IN_FAMILY")
    elif target_rows[0].get("kind")!="MATCHED_NONINFERIORITY":
        errors.append("TARGET_PREDICATE_NOT_MATCHED_NONINFERIORITY")

    claims=evidence.get("claims")
    if not isinstance(claims,list):
        claims=[]
        errors.append("EVIDENCE_CLAIMS_NOT_LIST")
    by_pid={}
    for c in claims:
        if isinstance(c,Mapping) and isinstance(c.get("predicate_id"),str):
            if c["predicate_id"] in by_pid:
                errors.append("DUPLICATE_EVIDENCE_CLAIM:"+c["predicate_id"])
            by_pid[c["predicate_id"]]=c

    already_proved=[]
    for pid in ids:
        if pid==target_predicate:
            continue
        c=by_pid.get(pid)
        if not isinstance(c,Mapping) or c.get("state")!="PROVED":
            errors.append("OTHER_FAMILY_PREDICATE_NOT_PROVED:"+pid)
            continue
        if c.get("independent_or_objective") is not True:
            errors.append("OTHER_FAMILY_PREDICATE_NOT_INDEPENDENT:"+pid)
        if c.get("scope_complete") is not True:
            errors.append("OTHER_FAMILY_PREDICATE_SCOPE_INCOMPLETE:"+pid)
        already_proved.append(pid)

    candidates=reconciliation.get("candidate_predicate_witnesses")
    if not isinstance(candidates,list):
        candidates=[]
        errors.append("RECONCILIATION_CANDIDATES_NOT_LIST")
    matches=[
        c for c in candidates
        if isinstance(c,Mapping)
        and c.get("predicate_id")==target_predicate
        and c.get("family")==family
    ]
    if len(matches)!=1:
        errors.append("TARGET_ATOMIC_CEILING_CANDIDATE_NOT_UNIQUE")
        atomic=None
    else:
        atomic=matches[0]
        if atomic.get("mode")!="ABSOLUTE_DOMINANCE":
            errors.append("TARGET_ATOMIC_MODE_NOT_ABSOLUTE_DOMINANCE")
        if atomic.get("contamination_clean") is not True:
            errors.append("TARGET_ATOMIC_CONTAMINATION_NOT_CLEAN")
        if atomic.get("binds_frozen_protocol") is not True:
            errors.append("TARGET_ATOMIC_DOES_NOT_BIND_FROZEN_PROTOCOL")
        if atomic.get("closes_entire_predicate") is not True:
            errors.append("TARGET_ATOMIC_DOES_NOT_CLOSE_PREDICATE")
        result=atomic.get("result")
        if not isinstance(result,Mapping):
            errors.append("TARGET_ATOMIC_RESULT_MISSING")
        else:
            if result.get("direction")!="higher":
                errors.append("TARGET_ATOMIC_DIRECTION_INVALID")
            if result.get("brain_lower_bound")!=1.0:
                errors.append("TARGET_ATOMIC_NOT_AT_CEILING")
            if result.get("theoretical_upper_bound")!=1.0:
                errors.append("TARGET_THEORETICAL_CEILING_NOT_ONE")

    fmap=behavioral_registry.get("family_to_residual_contracts")
    mapped=fmap.get(family) if isinstance(fmap,Mapping) else None
    behavior=atomic.get("behavior_id") if isinstance(atomic,Mapping) else None
    if not isinstance(behavior,str) or mapped!=[behavior]:
        errors.append("FAMILY_NOT_EXACT_SINGLE_RESIDUAL_CONTRACT")

    cv=behavioral_reduction.get("contract_verdict")
    passed_contracts=cv.get("passed_contracts") if isinstance(cv,Mapping) else None
    if not isinstance(passed_contracts,list) or behavior not in passed_contracts:
        errors.append("RESIDUAL_CONTRACT_BEHAVIORAL_PASS_MISSING")
    fv=behavioral_reduction.get("family_verdict")
    passed_families=fv.get("passed_families") if isinstance(fv,Mapping) else None
    if not isinstance(passed_families,list) or family not in passed_families:
        errors.append("FAMILY_BEHAVIORAL_PASS_MISSING")

    protocol=_unique_protocol(protocols,family)
    if protocol is None:
        errors.append("FAMILY_PROTOCOL_NOT_UNIQUE_OR_MISSING")
    elif protocol.get("status")!="DEFINED_RESULT_OPEN":
        errors.append("FAMILY_PROTOCOL_NOT_OPEN")

    if errors:
        return _fail(*errors)

    assert isinstance(atomic,Mapping) and isinstance(behavior,str)
    witness={
        "id":f"{family}_POSTWAVE_COMPOSITE_CEILING_ABSOLUTE_DOMINANCE_20261002_V1",
        "family":family,
        "mode":"ABSOLUTE_DOMINANCE",
        "verified":False,
        "independent":False,
        "contamination_clean":True,
        "binds_frozen_protocol":True,
        "scope_relation":"PROVEN_STRONGER",
        "closes_entire_protocol":True,
        "source_behavior_id":behavior,
        "source_target_predicate":target_predicate,
        "source_case_count":atomic.get("source_case_count"),
        "source_terminal_full_result_sha256":atomic.get("source_terminal_full_result_sha256"),
        "atomic_basis":{
            "target_ceiling_predicate":target_predicate,
            "already_proved_predicates":sorted(already_proved),
            "family_predicates":sorted(ids),
            "registry_lossless_decomposition":True,
        },
        "result":{
            "direction":"higher",
            "brain_lower_bound":1.0,
            "theoretical_upper_bound":1.0,
        },
        "reason":"LOSSLESS_FAMILY_ATOMIC_DECOMPOSITION_COMPLETE_AT_COMPOSITE_CEILING__TARGET_MATCHED_SUCCESS_AT_THEORETICAL_CEILING_AND_ALL_OTHER_FAMILY_ATOMICS_ALREADY_INDEPENDENTLY_PROVED",
    }
    return {
        "schema":SCHEMA,
        "status":"CANDIDATE_FAMILY_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "pass":True,
        "errors":[],
        "family":family,
        "target_predicate":target_predicate,
        "candidate_witness":witness,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
