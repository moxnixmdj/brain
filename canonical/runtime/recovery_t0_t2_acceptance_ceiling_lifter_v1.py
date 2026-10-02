"""Fail-closed lifter for the frozen T0/T2 recovery acceptance ceiling.

This compiler never grants ownership by itself. It recognizes only the exact
SELF_VERIFICATION_DEBUGGING_AND_RECOVERY -> TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001
scope relation, exact frozen P1 binding, and immutable terminal V3 T0/T2 receipts.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_RECOVERY_T0_T2_ACCEPTANCE_CEILING_LIFTER_V1"
FAMILY="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
BINDING_SHA="8703c6aa08227467a619a7ae90d0d61f8e54da39"
TERMINAL_SHA256="f4bec690aa0580cb532dbfd5985705bae8d153c9df31ffdf460b02f8b152e0f2"
PREDICATE_CAUSAL="RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR"
PREDICATE_INVARIANT="RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES"

REQ_CHECKS={
"EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
"FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
"NOMINATED_REPAIR_IS_FALSIFIABLE",
"NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
"SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
"NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
"AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
"MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
TARGET_DIMS={
"semantic self-check","counterexample discovery","earliest causal failure localization",
"repair selection","recovery after injected failure",
}
MUTATION_RULE="ALL_APPLICABLE_LOAD_BEARING_P1_MUTATIONS_MUST_BE_REJECTED_OR_CAUSE_PARENT_TERMINAL_ACCEPTANCE_FAILURE"
WEAK_EARLIEST_DISJUNCTION="EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE"
STRICT_EARLIEST_CHECK="EARLIEST_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE"
ROOT=Path(__file__).resolve().parents[2]
P1_SCOPE_QUARANTINE="canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"

def _scope_quarantine_error()->str|None:
    try:
        q=json.loads((ROOT/P1_SCOPE_QUARANTINE).read_text(encoding="utf-8"))
    except Exception:
        return "P1_EXECUTION_SCOPE_QUARANTINE_UNREADABLE"
    blocked=q.get("quarantine_pending_independent_verification")
    if isinstance(blocked,list) and "P1_TO_RECOVERY_ACCEPTANCE_SEMANTIC_TRANSPORT" in blocked:
        return "P1_EXECUTED_TERMINAL_SCOPE_MISMATCH_QUARANTINE_ACTIVE"
    return None

def _semantic_relation_errors(relation:Mapping[str,Any])->list[str]:
    """Reject semantic weakening even if the execution-scope quarantine is later cleared."""
    errors:list[str]=[]
    maps=relation.get("target_dimension_to_source_checks")
    if isinstance(maps,Mapping):
        earliest=maps.get("earliest causal failure localization")
        if not isinstance(earliest,list) or STRICT_EARLIEST_CHECK not in earliest:
            errors.append("RELATION_STRICT_EARLIEST_TARGET_HAS_NO_STRICT_SOURCE_PROOF")
        if isinstance(earliest,list) and WEAK_EARLIEST_DISJUNCTION in earliest:
            errors.append("RELATION_EARLIEST_TARGET_WEAKENED_TO_EARLIEST_OR_CRITICAL")
    ceilings=relation.get("acceptance_to_objective_floor_ceiling")
    causal=ceilings.get("causal_localization") if isinstance(ceilings,Mapping) else None
    if isinstance(causal,Mapping) and causal.get("source_check")==WEAK_EARLIEST_DISJUNCTION:
        errors.append("CAUSAL_LOCALIZATION_CEILING_DERIVED_FROM_WEAKER_DISJUNCTION")
    return sorted(set(errors))

def _fail(errors:list[str])->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
            "candidate_witness":None,"capability_credit_delta":0,"family_credit_delta":0,
            "promotion_authority":False}

def _protocol(doc:Mapping[str,Any])->Mapping[str,Any]|None:
    rows=doc.get("protocols")
    if not isinstance(rows,list): return None
    found=[x for x in rows if isinstance(x,Mapping) and x.get("family")==FAMILY]
    return found[0] if len(found)==1 else None

def _predicate(doc:Mapping[str,Any],pid:str)->Mapping[str,Any]|None:
    rows=doc.get("predicates") or doc.get("claims")
    if not isinstance(rows,list): return None
    found=[x for x in rows if isinstance(x,Mapping) and (x.get("id") or x.get("predicate_id"))==pid]
    return found[0] if len(found)==1 else None

def _receipt(terminal:Mapping[str,Any],portfolio:str)->Mapping[str,Any]|None:
    wave=((terminal.get("reduction_input") or {}).get("wave") or {})
    parents=wave.get("parent_portfolio_receipts")
    rows=parents.get(portfolio) if isinstance(parents,Mapping) else None
    if not isinstance(rows,list): return None
    found=[x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR]
    return found[0] if len(found)==1 else None

def evaluate(*,protocols:Mapping[str,Any],registry:Mapping[str,Any],predicates:Mapping[str,Any],
             binding:Mapping[str,Any],terminal:Mapping[str,Any],relation:Mapping[str,Any])->dict[str,Any]:
    e:list[str]=[]
    quarantine_error=_scope_quarantine_error()
    if quarantine_error is not None:
        e.append(quarantine_error)
    e.extend(_semantic_relation_errors(relation))
    p=_protocol(protocols)
    if p is None: e.append("RECOVERY_PROTOCOL_MISSING_OR_DUPLICATE")
    else:
        if p.get("status")!="DEFINED_RESULT_OPEN": e.append("RECOVERY_PROTOCOL_NOT_OPEN")
        if p.get("proof_mode")!="MATCHED_CAUSAL_INTERVENTION_PROTOCOL": e.append("RECOVERY_PROTOCOL_MODE_DRIFT")
        dims=p.get("task_dimensions")
        if not isinstance(dims,list) or set(dims)!=TARGET_DIMS: e.append("RECOVERY_TASK_DIMENSIONS_DRIFT")
        acc=str(p.get("acceptance") or "")
        for phrase in ("terminal-recovery","causal-localization","zero critical misses"):
            if phrase not in acc: e.append("RECOVERY_ACCEPTANCE_RULE_DRIFT:"+phrase)

    fmap=registry.get("family_to_residual_contracts")
    if not isinstance(fmap,Mapping) or fmap.get(FAMILY)!=[BEHAVIOR]:
        e.append("RECOVERY_NOT_EXACT_SINGLE_RESIDUAL_CONTRACT")

    pc=_predicate(predicates,PREDICATE_CAUSAL)
    pi=_predicate(predicates,PREDICATE_INVARIANT)
    if pc is None or "terminal-recovery and causal-localization bounds" not in str(pc.get("acceptance") or ""):
        e.append("CAUSAL_PREDICATE_DRIFT")
    if pi is None or str(pi.get("acceptance") or "")!="Deterministic fail-closed invariants have zero critical misses.":
        e.append("INVARIANT_PREDICATE_DRIFT")

    if binding.get("behavior_id")!=BEHAVIOR: e.append("BINDING_BEHAVIOR_DRIFT")
    if binding.get("proof_mode")!="T0_T2_MULTIPLEXED_DETERMINISTIC_INTERVENTION_RESCUE_GATE":
        e.append("BINDING_PROOF_MODE_DRIFT")
    if binding.get("portfolio_bindings")!=["T0","T2"]: e.append("BINDING_PORTFOLIO_DRIFT")
    checks=((binding.get("evaluator") or {}).get("required_checks"))
    if not isinstance(checks,list) or not REQ_CHECKS.issubset(set(checks)): e.append("LOAD_BEARING_CHECKS_INCOMPLETE")
    if ((binding.get("evaluator") or {}).get("mutation_acceptance"))!=MUTATION_RULE:
        e.append("FAIL_CLOSED_MUTATION_RULE_DRIFT")
    surfaces=((binding.get("scope_accounting") or {}).get("represented_terminal_surfaces"))
    if not isinstance(surfaces,list) or "RECOVERY_SCOPE_COMPOSITION" not in surfaces:
        e.append("RECOVERY_SCOPE_SURFACE_MISSING")
    ta=binding.get("terminal_acceptance") or {}
    if ta.get("any_load_bearing_p1_failure_blocks_behavior_proof") is not True:
        e.append("LOAD_BEARING_FAILURE_NOT_BLOCKING")

    if relation.get("schema")!="PROJECT_BRAIN_RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1":
        e.append("RELATION_SCHEMA_DRIFT")
    if relation.get("family")!=FAMILY or relation.get("source_behavior_id")!=BEHAVIOR:
        e.append("RELATION_SCOPE_DRIFT")
    if ((relation.get("source_binding") or {}).get("git_blob_sha"))!=BINDING_SHA:
        e.append("RELATION_BINDING_SHA_DRIFT")
    maps=relation.get("target_dimension_to_source_checks")
    if not isinstance(maps,Mapping) or set(maps)!=TARGET_DIMS:
        e.append("RELATION_DIMENSION_MAP_INCOMPLETE")
    else:
        for dim,src in maps.items():
            if not isinstance(src,list) or not src or not set(src).issubset(REQ_CHECKS):
                e.append("RELATION_CHECK_NOT_LOAD_BEARING:"+str(dim))

    if terminal.get("status")!="ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        e.append("TERMINAL_RESULT_NOT_IMMUTABLE_PASS")
    if ((terminal.get("artifact") or {}).get("full_result_sha256"))!=TERMINAL_SHA256:
        e.append("TERMINAL_FULL_RESULT_SHA_DRIFT")
    total=0
    for portfolio in ("T0","T2"):
        r=_receipt(terminal,portfolio)
        if r is None: e.append("RECOVERY_RECEIPT_MISSING:"+portfolio); continue
        if r.get("binding_blob")!=BINDING_SHA: e.append("RECOVERY_BINDING_BLOB_DRIFT:"+portfolio)
        for k in ("direct_instrumentation_pass","load_bearing","parent_terminal_acceptance_pass"):
            if r.get(k) is not True: e.append("RECOVERY_RECEIPT_NOT_PASS:"+portfolio+":"+k)
        if r.get("case_replaced") is not False or r.get("tuning_replay") is not False or r.get("result_to_runtime_feedback") is not False:
            e.append("RECOVERY_RECEIPT_CONTAMINATED:"+portfolio)
        cid=str(r.get("case_id") or "")
        try: n=int(cid.rsplit("::",1)[-1])
        except Exception: n=-1
        if n!=30: e.append("RECOVERY_CASE_COUNT_DRIFT:"+portfolio)
        else: total+=n
    guards=terminal.get("result_guards")
    if not isinstance(guards,Mapping) or guards.get("no_case_replacement") is not True or guards.get("no_tuning_replay") is not True or guards.get("result_to_runtime_feedback_during_wave") is not False:
        e.append("TERMINAL_CONTAMINATION_GUARDS_FAIL")

    if e: return _fail(e)
    witness={
      "id":"RECOVERY_T0_T2_ABSOLUTE_DOMINANCE_20261002_V1",
      "family":FAMILY,
      "mode":"ABSOLUTE_DOMINANCE",
      "verified":False,
      "independent":False,
      "contamination_clean":True,
      "binds_frozen_protocol":True,
      "scope_relation":"PROVEN_STRONGER",
      "closes_entire_protocol":True,
      "source_behavior_id":BEHAVIOR,
      "source_case_count":total,
      "source_terminal_full_result_sha256":TERMINAL_SHA256,
      "result":{"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0},
      "hard_invariants":{"critical_fail_closed_misses":{"direction":"lower","brain_upper_bound":0.0,"theoretical_lower_bound":0.0}},
      "reason":"EXACT_SINGLE_RESIDUAL_RECOVERY_CONTRACT__FROZEN_T0_T2_CAUSAL_LOCALIZATION_RESCUE_AND_FAIL_CLOSED_CHECKS_ALL_PASS_AT_OBJECTIVE_BOUNDS",
    }
    return {"schema":SCHEMA,"status":"CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED","pass":True,
            "errors":[],"source_case_count":total,"candidate_witness":witness,
            "capability_credit_delta":0,"family_credit_delta":0,"promotion_authority":False}
