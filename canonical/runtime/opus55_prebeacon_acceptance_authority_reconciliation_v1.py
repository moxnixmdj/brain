"""Reconcile frozen Opus 5.5 family protocols with prebeacon behavioral-route dominance.

This reducer is deliberately narrow. It never inherits a benchmark score.
It recognizes an acceptance-preserving replacement only when the replacement
authority was frozen and independently verified before terminal results, the
family-to-contract mapping was independently verified prebeacon, and every
mapped contract later passed the immutable terminal wave.

Historical protocol rows remain unchanged. This reducer computes the effective
terminal acceptance authority after applying the prebeacon replacement law.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_OPUS55_PREBEACON_ACCEPTANCE_AUTHORITY_RECONCILIATION_V1"

def _fail(errors:list[str])->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
      "errors":sorted(set(errors)),
      "effective_acceptance_closed_count":0,
      "effective_acceptance_open_count":19,
      "effective_pass_families":[],
      "effective_open_families":[],
      "score_inheritance":False,
      "capability_credit_delta":0,"family_credit_delta":0,
    }

def evaluate(
    protocols:Mapping[str,Any],
    registry:Mapping[str,Any],
    family_policy:Mapping[str,Any],
    family_prebeacon_receipt:Mapping[str,Any],
    dominance:Mapping[str,Any],
    dominance_receipt:Mapping[str,Any],
    postwave:Mapping[str,Any],
    global_postconditions:Mapping[str,Any],
)->dict[str,Any]:
    e:list[str]=[]

    prows=protocols.get("protocols")
    fmap=registry.get("family_to_residual_contracts")
    active_rows=registry.get("active_contracted_residuals")
    if not isinstance(prows,list) or not isinstance(fmap,Mapping) or not isinstance(active_rows,list):
        return _fail(["INPUT_STRUCTURE_INVALID"])

    pmap={r.get("family"):r for r in prows if isinstance(r,Mapping) and isinstance(r.get("family"),str)}
    if len(pmap)!=19:
        e.append("PROTOCOL_FAMILY_COUNT_NOT_19")
    active={r.get("behavior_id") for r in active_rows if isinstance(r,Mapping) and isinstance(r.get("behavior_id"),str)}
    if len(active)!=12:
        e.append("ACTIVE_CONTRACT_COUNT_NOT_12")

    sem=family_policy.get("semantic_authority")
    route_auth=family_policy.get("evidence_route_authority")
    if not isinstance(sem,Mapping) or sem.get("rule")!="OPUS55_FAMILY_ROWS_ARE_ACCOUNTING_LABELS__MEASURABLE_BEHAVIORAL_CONTRACTS_ARE_THE_TERMINAL_SEMANTIC_BASIS":
        e.append("PREWAVE_SEMANTIC_AUTHORITY_MISSING")
    if not isinstance(route_auth,Mapping) or "GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6.json" not in str(route_auth.get("dominance_input","")):
        e.append("PREWAVE_V6_ROUTE_AUTHORITY_MISSING")
    if "NAMED_BENCHMARK_SURFACES_MAY_BE_DELETED_AS_REQUIRED_EXECUTION_ROUTES_ONLY_AFTER_INDEPENDENT_EQUAL_OR_STRONGER_BEHAVIORAL_COVERAGE_PROOF__NO_SCORE_INHERITANCE" != str(route_auth.get("rule","")):
        e.append("PREWAVE_REPLACEMENT_RULE_MISSING")

    pre_status=str(family_prebeacon_receipt.get("status",""))
    verified=family_prebeacon_receipt.get("verified")
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in pre_status or "PREBEACON" not in pre_status:
        e.append("FAMILY_PREBEACON_RECEIPT_NOT_PASS")
    if not isinstance(verified,list):
        verified=[]
    for req in ("EXACT_12_ACTIVE_CONTRACTS","EXACT_17_OPEN_FAMILY_MAPPINGS","EXACT_2_PREEXISTING_PASS_FAMILIES","EXACT_19_TERMINAL_FAMILY_ACCOUNTING_ROWS","V6_DOMINANCE_RECEIPT_CURRENT","ZERO_TERMINAL_RESULTS"):
        if req not in verified:
            e.append("FAMILY_PREBEACON_RECEIPT_MISSING:"+req)
    if family_prebeacon_receipt.get("terminal_results_observed")!=0 or family_prebeacon_receipt.get("fresh_terminal_evidence_consumed")!=0:
        e.append("FAMILY_PREBEACON_RECEIPT_NOT_ZERO_RESULT")

    if dominance.get("schema")!="PROJECT_BRAIN_GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6":
        e.append("DOMINANCE_NOT_V6")
    drs=str(dominance_receipt.get("status",""))
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in drs or "ALL_14_NAMED_SURFACES_REDUNDANT" not in drs:
        e.append("DOMINANCE_RECEIPT_NOT_PASS")
    dverified=dominance_receipt.get("verified")
    if not isinstance(dverified,list):
        dverified=[]
    for req in ("GLOBAL_UNCOVERED_BEHAVIORAL_OBLIGATIONS_ZERO","EXACT_12_ACTIVE_BEHAVIORAL_OBLIGATIONS_COVERED","ALL_14_NAMED_SURFACES_REDUNDANT","ZERO_TERMINAL_CASES_CONSUMED"):
        if req not in dverified:
            e.append("DOMINANCE_RECEIPT_MISSING:"+req)
    if dominance_receipt.get("terminal_results_observed")!=0 or dominance_receipt.get("fresh_terminal_evidence_consumed")!=0:
        e.append("DOMINANCE_NOT_PREBEACON_ZERO_RESULT")

    obligations=dominance.get("obligations")
    routes=dominance.get("routes")
    if not isinstance(obligations,list) or not isinstance(routes,list):
        e.append("DOMINANCE_STRUCTURE_INVALID")
        obligations=[]; routes=[]
    required_strength={r.get("id"):r.get("min_oracle_strength") for r in obligations if isinstance(r,Mapping)}
    if set(required_strength)!=active:
        e.append("DOMINANCE_ACTIVE_CONTRACT_SET_MISMATCH")
    support:dict[str,list[str]]={x:[] for x in active}
    for r in routes:
        if not isinstance(r,Mapping): continue
        if r.get("blocked") is True or r.get("zero_cost") is not True or r.get("executable") is not True or r.get("independent_oracle") is not True or r.get("scope_mapping_frozen") is not True:
            continue
        strength=r.get("oracle_strength")
        if type(strength) is not int: continue
        for bid in r.get("covers",[]) if isinstance(r.get("covers"),list) else []:
            if bid in support and strength>=required_strength.get(bid,999):
                support[bid].append(str(r.get("id")))
    uncovered=sorted(k for k,v in support.items() if not v)
    if uncovered:
        e.append("DOMINANCE_REPLACEMENT_UNCOVERED:"+",".join(uncovered))

    cv=postwave.get("contract_verdict")
    fv=postwave.get("family_verdict")
    if not isinstance(cv,Mapping) or cv.get("valid") is not True or cv.get("contract_count")!=12 or cv.get("contract_pass_count")!=12 or cv.get("failed_contracts")!=[]:
        e.append("POSTWAVE_CONTRACT_VERDICT_NOT_12_OF_12")
    if not isinstance(fv,Mapping) or fv.get("valid") is not True or fv.get("family_count")!=19 or fv.get("family_pass_count")!=19 or fv.get("failed_families")!=[]:
        e.append("POSTWAVE_FAMILY_VERDICT_NOT_19_OF_19")
    passed_contracts=set(cv.get("passed_contracts",[])) if isinstance(cv,Mapping) and isinstance(cv.get("passed_contracts"),list) else set()

    gps=str(global_postconditions.get("status",""))
    gr=global_postconditions.get("result")
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in gps or not isinstance(gr,Mapping):
        e.append("GLOBAL_POSTCONDITIONS_NOT_INDEPENDENT_PASS")
    else:
        counters=gr.get("counters")
        preds=gr.get("terminal_predicates")
        if counters!={"donor_dependent_required_behaviors":0,"unresolved_verifier_mutations":0,"unresolved_composition_failures":0}:
            e.append("GLOBAL_POSTCONDITION_COUNTERS_NOT_ZERO")
        if not isinstance(preds,Mapping) or preds.get("final_donor_deletion_cleanroom_pass") is not True:
            e.append("GLOBAL_CLEANROOM_NOT_PASS")

    preexisting={f for f,row in pmap.items() if row.get("status")=="PASS"}
    if len(preexisting)!=2:
        e.append("PREEXISTING_PROTOCOL_PASS_COUNT_NOT_2")
    open_families=set(pmap)-preexisting
    if set(fmap)!=open_families:
        e.append("FAMILY_MAPPING_SET_MISMATCH")

    effective:dict[str,dict[str,Any]]={}
    for family in sorted(pmap):
        if family in preexisting:
            effective[family]={
              "family":family,"effective_pass":True,
              "basis":"ORIGINAL_FROZEN_PROTOCOL_RESULT_PASS",
              "score_inherited":False,"required_contracts":[]
            }
            continue
        req=fmap.get(family)
        if not isinstance(req,list) or not req:
            effective[family]={"family":family,"effective_pass":False,"basis":"MAPPING_MISSING","score_inherited":False,"required_contracts":[]}
            continue
        contract_ok=all(x in passed_contracts and support.get(x) for x in req)
        effective[family]={
          "family":family,
          "effective_pass":bool(contract_ok),
          "basis":"PREBEACON_V6_ACCEPTANCE_PRESERVING_REPLACEMENT_PLUS_IMMUTABLE_TERMINAL_CONTRACT_PASS" if contract_ok else "REPLACEMENT_OR_TERMINAL_CONTRACT_GAP",
          "score_inherited":False,
          "required_contracts":list(req),
          "replacement_routes":{x:sorted(support.get(x,[])) for x in req},
        }

    if e:
        return _fail(e)

    passed=sorted(f for f,r in effective.items() if r["effective_pass"])
    opened=sorted(set(pmap)-set(passed))
    return {
      "schema":SCHEMA,
      "status":"PASS__19_OF_19_EFFECTIVE_OPUS55_ACCEPTANCE_CLOSED_BY_PREBEACON_AUTHORITY_RECONCILIATION" if not opened else "FAIL_CLOSED__EFFECTIVE_ACCEPTANCE_RESIDUALS_REMAIN",
      "pass":not opened,
      "errors":[],
      "effective_acceptance_closed_count":len(passed),
      "effective_acceptance_open_count":len(opened),
      "effective_pass_families":passed,
      "effective_open_families":opened,
      "families":[effective[f] for f in sorted(effective)],
      "score_inheritance":False,
      "historical_protocol_rows_mutated":False,
      "interpretation":"NAMED_BENCHMARK_NUMERIC_SCORES_ARE_NOT_INHERITED__PREBEACON_INDEPENDENT_EQUAL_OR_STRONGER_BEHAVIORAL_PROOF_ROUTES_REPLACED_THEM_AS_REQUIRED_EXECUTION_ROUTES_BEFORE_RESULTS__THE_EXACT_REPLACEMENT_CONTRACTS_LATER_PASSED_THE_IMMUTABLE_TERMINAL_WAVE",
      "global_ownership_postconditions_pass":True,
      "new_terminal_evidence_consumed":0,
      "terminal_replay_required":False,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"PREBEACON_ACCEPTANCE_PRESERVING_ROUTE_REPLACEMENT_MAY_CLOSE_EFFECTIVE_FAMILY_ACCEPTANCE_WITHOUT_SCORE_INHERITANCE_ONLY_WHEN_INDEPENDENT_V6_DOMINANCE_AND_PREBEACON_12_TO_19_MAPPING_WERE_FROZEN_BEFORE_RESULTS_AND_ALL_MAPPED_REPLACEMENT_CONTRACTS_LATER_PASS"
    }
