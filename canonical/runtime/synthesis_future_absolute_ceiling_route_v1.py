"""Fail-closed pre-exposure verifier for the future synthesis absolute-ceiling route.

This verifies only that the route is a truthful, frozen, future-only sufficient
condition for comparator elimination. It consumes no cases and grants no
acceptance/capability/family/execution/promotion credit.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
ROUTE=ROOT/"canonical/governance/SYNTHESIS_FUTURE_ABSOLUTE_CEILING_ROUTE_V1.json"
PROTOCOLS=ROOT/"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
TARGETS=ROOT/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json"
SUPER=ROOT/"canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"
SUITES=ROOT/"canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json"

SCHEMA="PROJECT_BRAIN_SYNTHESIS_FUTURE_ABSOLUTE_CEILING_ROUTE_VERDICT_V1"
FAMILY="COMMUNICATION_AND_SYNTHESIS"
TARGET="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
BEHAVIOR="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
DIMS=[
 "claim-to-source fidelity","required evidence coverage",
 "uncertainty/disagreement preservation","audience adaptation",
 "format/style constraints","compression without decision-relevant loss",
]
ATOMS={
 "dimension:claim_to_source_fidelity","dimension:required_evidence_coverage",
 "dimension:uncertainty_and_disagreement_preservation","dimension:audience_adaptation",
 "dimension:format_and_style_constraints","dimension:compression_without_decision_relevant_loss",
 "metric:matched_quality","metric:required_claim_coverage",
}
METRICS={"matched_quality_noninferiority","required_claim_coverage_noninferiority"}

def load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def blob_sha(p:Path)->str:
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
def fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
            "route_preexposure_valid":False,"exact_opus_required_if_brain_hits_ceiling":None,
            "new_reality_units_consumed":0,"acceptance_credit_delta":0,"capability_credit_delta":0,
            "family_credit_delta":0,"execution_authority":False,"promotion_authority":False}

def one(rows,key,value):
    xs=[x for x in rows if isinstance(x,Mapping) and x.get(key)==value] if isinstance(rows,list) else []
    return xs[0] if len(xs)==1 else None

def evaluate(route:Mapping[str,Any],protocols:Mapping[str,Any],targets:Mapping[str,Any],
             superportfolio:Mapping[str,Any],suites:Mapping[str,Any],shas:Mapping[str,str])->dict[str,Any]:
    e=[]
    if route.get("family")!=FAMILY or route.get("target_predicate_id")!=TARGET or route.get("behavior_id")!=BEHAVIOR:
        e.append("ROUTE_IDENTITY_DRIFT")

    auth=route.get("authority")
    expected={
      "protocols":("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",shas["protocols"]),
      "target_normalization":("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json",shas["targets"]),
      "matched_superportfolio":("canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json",shas["super"]),
      "prewave_absolute_suite":("canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json",shas["suites"]),
    }
    if not isinstance(auth,Mapping): e.append("AUTHORITY_MISSING")
    else:
      for k,(p,s) in expected.items():
        r=auth.get(k)
        if not isinstance(r,Mapping) or r.get("path")!=p or r.get("git_blob_sha")!=s:
            e.append("AUTHORITY_MISMATCH:"+k)

    p=one(protocols.get("protocols"),"family",FAMILY)
    if not isinstance(p,Mapping): e.append("SYNTHESIS_PROTOCOL_NOT_UNIQUE")
    else:
      if p.get("proof_mode")!="MATCHED_GROUNDED_SYNTHESIS_NONINFERIORITY": e.append("PROTOCOL_MODE_DRIFT")
      if p.get("task_dimensions")!=DIMS: e.append("PROTOCOL_DIMENSIONS_DRIFT")
      if not {"unsupported_material_claim_rate","required_claim_coverage","independent_quality_score"}.issubset(set(p.get("primary_metrics") or [])):
          e.append("PROTOCOL_METRICS_DRIFT")
      acc=str(p.get("acceptance") or "")
      if "Zero unsupported material claims" not in acc or "matched quality/coverage" not in acc:
          e.append("PROTOCOL_ACCEPTANCE_DRIFT")

    t=one(targets.get("targets"),"predicate_id",TARGET)
    if not isinstance(t,Mapping): e.append("TARGET_NOT_UNIQUE")
    else:
      if set(t.get("required_atoms") or [])!=ATOMS: e.append("TARGET_ATOMS_DRIFT")
      req=t.get("metric_requirements")
      got={x.get("metric") for x in req if isinstance(x,Mapping) and x.get("direction")=="higher" and x.get("threshold")==0} if isinstance(req,list) else set()
      if got!=METRICS: e.append("TARGET_METRIC_REQUIREMENTS_DRIFT")

    sf=one(superportfolio.get("core_families"),"family",FAMILY)
    if not isinstance(sf,Mapping): e.append("SUPERPORTFOLIO_SYNTHESIS_ROW_MISSING")
    else:
      if set(sf.get("metrics") or [])!={"matched_quality","coverage","unsupported_material_claims"}:
          e.append("SUPERPORTFOLIO_METRIC_DRIFT")

    suite=one(suites.get("suites"),"behavior_id",BEHAVIOR)
    src=[]
    if not isinstance(suite,Mapping): e.append("PREWAVE_SYNTHESIS_SUITE_MISSING")
    else:
      src=suite.get("frozen_population") or []
      if route.get("preexposure_scope_blueprint",{}).get("source_classes")!=src:
          e.append("SOURCE_CLASSES_NOT_EXACT_PREWAVE_SUITE")
      need={"ZERO_UNSUPPORTED_MATERIAL_CLAIMS","100_PERCENT_REQUIRED_CLAIM_COVERAGE",
            "NO_DECISION_RELEVANT_EVIDENCE_DROPPED","CONFLICT_AND_UNCERTAINTY_PRESERVED",
            "AUDIENCE_AND_FORMAT_CONSTRAINTS_PASS","IRRELEVANT_EVIDENCE_EXCLUDED_WITHOUT_DELETING_REQUIRED_SUPPORT"}
      if not need.issubset(set(suite.get("oracle") or [])): e.append("PREWAVE_ORACLE_COVERAGE_DRIFT")

    if route.get("frozen_task_dimensions")!=DIMS: e.append("ROUTE_DIMENSIONS_DRIFT")
    scope=route.get("preexposure_scope_blueprint")
    if not isinstance(scope,Mapping): e.append("SCOPE_BLUEPRINT_MISSING")
    else:
      for k in ("generated_now","exposed_now","beacon_known_now","adaptive_case_selection","case_replacement","tuning_replay","result_feedback"):
        if scope.get(k) is not False: e.append("PREEXPOSURE_FLAG_MUST_BE_FALSE:"+k)
      if scope.get("future_beacon_required") is not True: e.append("FUTURE_BEACON_NOT_REQUIRED")
      if scope.get("dimension_cells_per_source")!=len(DIMS): e.append("DIMENSION_CELL_COUNT_DRIFT")
      if scope.get("case_count")!=len(src)*len(DIMS): e.append("CASE_COUNT_NOT_CARTESIAN_BLUEPRINT")
      seed=str(scope.get("future_seed_rule") or "")
      if "FUTURE_POST_FREEZE_BEACON" not in seed or "CASE_ID" not in seed: e.append("FUTURE_SEED_RULE_INCOMPLETE")
      if not str(scope.get("payload_generation_state") or "").startswith("NOT_GENERATED"): e.append("PAYLOADS_PREMATURELY_GENERATED")

    scorer=route.get("scorer")
    if not isinstance(scorer,Mapping): e.append("SCORER_MISSING")
    else:
      if scorer.get("same_scorer_for_brain_and_comparator") is not True: e.append("SAME_SCORER_REQUIRED")
      q=scorer.get("matched_quality") or {}
      c=scorer.get("required_claim_coverage") or {}
      u=scorer.get("unsupported_material_claims") or {}
      if q.get("range")!=[0,1] or q.get("ceiling")!=1 or q.get("case_score")!="MIN_OF_SIX_FROZEN_DIMENSION_PASS_BITS":
          e.append("QUALITY_CEILING_SCORER_DRIFT")
      if c.get("range")!=[0,1] or c.get("ceiling")!=1:
          e.append("COVERAGE_CEILING_SCORER_DRIFT")
      if u.get("required_value")!=0: e.append("UNSUPPORTED_CLAIM_ZERO_GATE_DRIFT")

    scope_req=route.get("scope_completeness_requirement")
    if not isinstance(scope_req,Mapping): e.append("SCOPE_COMPLETENESS_REQUIREMENT_MISSING")
    else:
      if scope_req.get("current_state")!="PENDING_PREEXPOSURE__NO_SCOPE_COMPLETENESS_CLAIM__ZERO_CREDIT": e.append("SCOPE_COMPLETENESS_STATE_DRIFT")
      if scope_req.get("required_basis")!="EXACT_COMPLETE_TARGET_CASE_UNIVERSE": e.append("SCOPE_COMPLETENESS_BASIS_DRIFT")
      if "not itself" not in str(scope_req.get("explicit_nonclaim") or "").lower(): e.append("BLUEPRINT_NONCLAIM_MISSING")
      if "PERFECT_FINITE_SAMPLE" not in str(scope_req.get("forbidden") or ""): e.append("FINITE_SAMPLE_FIREWALL_MISSING")

    theorem=route.get("comparator_elimination_theorem")
    if not isinstance(theorem,Mapping) or theorem.get("route_kind")!="ABSOLUTE_CEILING_DOMINANCE_ON_EXACT_FUTURE_SCOPE":
        e.append("CEILING_THEOREM_MISSING")
    if route.get("existing_result_inputs")!=[]: e.append("POSTHOC_RESULT_TRANSPORT_FORBIDDEN")
    if route.get("new_reality_units_consumed")!=0 or route.get("incremental_spend_usd")!=0:
        e.append("ROUTE_PREFLIGHT_MUST_CONSUME_ZERO_REALITY_AND_SPEND")
    if route.get("execution_authority") is not False or route.get("promotion_authority") is not False:
        e.append("ROUTE_MUST_NOT_SELF_AUTHORIZE")

    if e: return fail(*e)
    return {
      "schema":SCHEMA,
      "status":"PASS__FUTURE_SYNTHESIS_CEILING_ROUTE_IS_PREEXPOSURE_AND_MATHEMATICALLY_SUFFICIENT__ZERO_CREDIT",
      "pass":True,
      "errors":[],
      "family":FAMILY,
      "target_predicate_id":TARGET,
      "future_case_count":len(src)*len(DIMS),
      "route_preexposure_valid":True,
      "ceiling_condition":{
        "matched_quality":1.0,
        "required_claim_coverage":1.0,
        "unsupported_material_claims":0,
      },
      "theorem":"WITH_IDENTICAL_BOUNDED_SCORER_ON_THE_EXACT_FUTURE_SCOPE__BRAIN_AT_1_0_QUALITY_AND_1_0_COVERAGE_CANNOT_BE_OUTSCORED_BY_ANY_COMPARATOR",
      "exact_opus_required_if_brain_hits_ceiling":False,
      "old_terminal_evidence_admissible":False,
      "scope_completeness_currently_proved":False,
      "required_scope_completeness_basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
      "remaining_before_execution":[
        "CONTENT_ADDRESSED_CASE_GENERATOR_AND_SOURCE_POOL_BINDING",
        "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_CERTIFICATE",
        "INDEPENDENT_SCOPE_AND_SCORER_VERIFICATION",
        "BRAIN_ROUTE_BINDING",
        "MACHINE_EXECUTION_AUTHORITY"
      ],
      "new_reality_units_consumed":0,
      "acceptance_credit_delta":0,"capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,
    }

def main()->int:
    out=evaluate(load(ROUTE),load(PROTOCOLS),load(TARGETS),load(SUPER),load(SUITES),{
      "protocols":blob_sha(PROTOCOLS),"targets":blob_sha(TARGETS),
      "super":blob_sha(SUPER),"suites":blob_sha(SUITES),
    })
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
