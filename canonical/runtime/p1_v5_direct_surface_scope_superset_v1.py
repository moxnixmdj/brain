"""P1 V5 direct-surface behavioral-scope superset verifier.

This verifier does NOT claim that a synthetic population is the private
FrontierCode/CursorBench/Recovery population. It proves a narrower statement:
all frozen P1 direct surfaces bind the same frozen P1 behavioral contract, V4
left exactly two whole-contract semantic residuals, and independently verified
V5 supplies those residuals while executable checks kill every frozen P1
mutation. Raw terminal receipts remain separate and immutable.
"""
from __future__ import annotations
import copy, json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V5_DIRECT_SURFACE_SCOPE_SUPERSET_VERDICT_V1"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
ROUTE="P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF"
P1_BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
MANIFEST="canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
DIRECT_ROUTES="canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json"
FOUR_CONTRACTS="canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"
V4_RESIDUAL="canonical/verification/P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V5_RECEIPT="canonical/verification/P1_TYPED_INTERVENTION_ENVELOPE_V5_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
TERMINAL_WAVE="canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
EXPECTED_SURFACES={
 "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
EXPECTED_CHECKS={
 "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
 "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
 "NOMINATED_REPAIR_IS_FALSIFIABLE",
 "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
 "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
 "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
 "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
 "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
EXPECTED_MUTATIONS={
 "SELECT_DOWNSTREAM_SYMPTOM","SELECT_LATER_CORRELATED_STEP",
 "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT","UNFALSIFIABLE_DIAGNOSIS",
 "REPAIR_TARGET_WITH_NO_RESCUE","FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
 "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN","SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS",
 "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
}
EXPECTED_RESIDUALS={"P1_EXPLICIT_SCOPE_FAILURE_CLASS","P1_HETEROGENEOUS_INTERVENTION_RESCUE"}

def _load(rel:str)->dict[str,Any]:
 v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError(rel+":NOT_OBJECT")
 return v

def _p1_receipt(wave:Mapping[str,Any],tier:str)->Mapping[str,Any]|None:
 rows=(((wave.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {}).get(tier,[])
 hits=[x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR]
 return hits[0] if len(hits)==1 else None

def _surface_rows(manifest:Mapping[str,Any])->dict[str,Mapping[str,Any]]:
 out={}
 for tier in ("T0","T2"):
  rows=(((manifest.get("portfolios") or {}).get(tier) or {}).get("surfaces") or [])
  for row in rows:
   if isinstance(row,Mapping) and ROUTE in (row.get("proof_routes") or []):
    out[f"{tier}/{row.get('id')}::{ROUTE}"]=row
 return out

def _score(case:Mapping[str,Any],public:Mapping[str,Any]|None=None):
 p=copy.deepcopy(public if public is not None else proof.public_task(case))
 out=candidate.solve(p)
 return out,proof.score_case(case,out)

def _mutation_audit()->dict[str,Any]:
 results={}
 single=proof.generate_case(71001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
 base,bv=_score(single); assert bv.get("pass") is True

 m=copy.deepcopy(base); m["cause_action_id"]="A2"; m["cause_action_ids"]=["A2"]; m["critical_action_id"]="A2"
 results["SELECT_DOWNSTREAM_SYMPTOM"]=proof.score_case(single,m).get("pass") is False

 delayed=proof.generate_case(71002,pattern="DELAYED",domain="CODE",kind="SCOPE")
 d,dv=_score(delayed); assert dv.get("pass") is True
 m=copy.deepcopy(d); m["cause_action_id"]="A4"; m["cause_action_ids"]=["A4"]; m["critical_action_id"]="A4"
 results["SELECT_LATER_CORRELATED_STEP"]=proof.score_case(delayed,m).get("pass") is False

 auth=proof.generate_case(71003,pattern="SINGLE",domain="BROWSER",kind="AUTHORITY")
 pub=copy.deepcopy(proof.public_task(auth))
 for row in pub["task"]["trajectory"]:
  if row["action_id"]=="A1":
   for check in row["checks"]:
    if check["pass"] is False: check["pass"]=True
 _,v=_score(auth,pub)
 results["IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT"]=v.get("pass") is False

 m=copy.deepcopy(base); m["diagnosis"]={"claim":"UNOBSERVABLE_FORCE","falsifiable":False,"supporting_receipts":[]}
 results["UNFALSIFIABLE_DIAGNOSIS"]=proof.score_case(single,m).get("pass") is False

 m=copy.deepcopy(base)
 m["repair_targets"]=[single["_intervention_model"]["downstream_symptom_repairs"][0]]
 results["REPAIR_TARGET_WITH_NO_RESCUE"]=proof.score_case(single,m).get("pass") is False

 amb=proof.generate_case(71004,pattern="AMBIGUOUS",domain="ARTIFACT",kind="SCOPE")
 a,av=_score(amb); assert av.get("pass") is True
 m=copy.deepcopy(a); m["cause_action_id"]="A1"
 results["FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE"]=proof.score_case(amb,m).get("pass") is False

 inter=proof.generate_case(71005,pattern="INTERACTION",domain="TOOL_API",kind="DEPENDENCY")
 pub=copy.deepcopy(proof.public_task(inter))
 for row in pub["task"]["trajectory"]:
  if row["action_id"]=="A3":
   row["depends_on"]=[x for x in row["depends_on"] if x!="A2"]
   row["reads"]=[x for x in row["reads"] if not x.endswith(":right")]
 _,v=_score(inter,pub)
 results["DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN"]=v.get("pass") is False

 tool=proof.generate_case(71006,pattern="SINGLE",domain="FILESYSTEM",kind="TOOL_CONTRACT")
 pub=copy.deepcopy(proof.public_task(tool))
 for row in pub["task"]["trajectory"]:
  if row["action_id"]=="A1":
   for check in row["checks"]:
    if check["pass"] is False: check["kind"]="AUTHORITY"
 _,v=_score(tool,pub)
 results["SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS"]=v.get("pass") is False

 prov=proof.generate_case(71007,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
 pub=copy.deepcopy(proof.public_task(prov))
 for row in pub["task"]["trajectory"]:
  for check in row["checks"]:
   if check["pass"] is False: check["evidence"]=[]
 out,v=_score(prov,pub)
 results["DROP_PROVENANCE_OR_DEPENDENCY_EDGE"]=out.get("status")=="FAIL_CLOSED" and v.get("pass") is False

 return {"all_frozen_mutations_killed":all(results.values()) and set(results)==EXPECTED_MUTATIONS,
         "mutation_count":len(results),"results":dict(sorted(results.items()))}

def evaluate(binding=None,manifest=None,routes=None,contracts=None,residual=None,v5=None,wave=None)->dict[str,Any]:
 binding=dict(binding or _load(P1_BINDING)); manifest=dict(manifest or _load(MANIFEST))
 routes=dict(routes or _load(DIRECT_ROUTES)); contracts=dict(contracts or _load(FOUR_CONTRACTS)); residual=dict(residual or _load(V4_RESIDUAL))
 v5=dict(v5 or _load(V5_RECEIPT)); wave=dict(wave or _load(TERMINAL_WAVE))
 errors=[]
 if binding.get("behavior_id")!=BEHAVIOR: errors.append("P1_BEHAVIOR_DRIFT")
 if set(binding.get("direct_surface_bindings") or [])!=EXPECTED_SURFACES: errors.append("P1_DIRECT_SURFACE_BINDING_DRIFT")
 ev=binding.get("evaluator") if isinstance(binding.get("evaluator"),Mapping) else {}
 if set(ev.get("required_checks") or [])!=EXPECTED_CHECKS: errors.append("FROZEN_REQUIRED_CHECK_SET_DRIFT")
 if set(ev.get("required_mutations") or [])!=EXPECTED_MUTATIONS: errors.append("FROZEN_REQUIRED_MUTATION_SET_DRIFT")

 surfaces=_surface_rows(manifest)
 if set(surfaces)!=EXPECTED_SURFACES: errors.append("MANIFEST_P1_SURFACE_SET_DRIFT")
 for key,row in surfaces.items():
  if row.get("direct_proof_contracts")!="canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json":
   errors.append("SURFACE_DIRECT_CONTRACT_DRIFT:"+key)
  if row.get("evaluator")!=DIRECT_ROUTES: errors.append("SURFACE_EVALUATOR_DRIFT:"+key)

 obligations=[x for x in (contracts.get("obligations") or []) if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR]
 if len(obligations)!=1: errors.append("FROZEN_P1_CONTRACT_OBLIGATION_COUNT")
 else:
  o=obligations[0]
  if o.get("route_id")!=ROUTE: errors.append("FROZEN_P1_CONTRACT_ROUTE_DRIFT")
  if o.get("universe")!="INTERVENTION_IDENTIFIED_REPLAYABLE_AGENT_TRAJECTORIES_WITH_HIDDEN_FAULT_METADATA": errors.append("FROZEN_P1_CONTRACT_UNIVERSE_DRIFT")
  if set(o.get("oracle") or [])!={"EARLIEST_CAUSAL_STEP_MATCH","REPAIR_RESCUES_TERMINAL_OUTCOME","SYMPTOM_ONLY_REPAIR_DOES_NOT_COUNT","NONIDENTIFIABLE_CASE_ABSTAINS"}: errors.append("FROZEN_P1_CONTRACT_ORACLE_DRIFT")
  if not set(o.get("mutations") or [])<=EXPECTED_MUTATIONS: errors.append("FROZEN_P1_CONTRACT_MUTATION_NOT_SUBSET_OF_BOUND_MUTATIONS")

 direct=[x for x in (routes.get("routes") or []) if isinstance(x,Mapping) and BEHAVIOR in (x.get("covers") or [])]
 if len(direct)!=1: errors.append("DIRECT_P1_ROUTE_COUNT")
 else:
  r=direct[0]
  if r.get("id")!="DIRECT_TRAJECTORY_CAUSAL_CONTRACT_SUITE": errors.append("DIRECT_P1_ROUTE_ID")
  if r.get("oracle")!="EXACT_INJECTED_CAUSE_LOCALIZATION_PLUS_REPAIR_RESCUE": errors.append("DIRECT_P1_ORACLE_DRIFT")
  for key in ("zero_cost","executable","independent_oracle","scope_mapping_frozen","contamination_boundary_frozen"):
   if r.get(key) is not True: errors.append("DIRECT_P1_ROUTE_FLAG:"+key)

 if not str(residual.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"): errors.append("V4_RESIDUAL_NOT_INDEPENDENT_PASS")
 rr=residual.get("result") if isinstance(residual.get("result"),Mapping) else {}
 if set(rr.get("residual_obligations") or [])!=EXPECTED_RESIDUALS: errors.append("V4_EXACT_RESIDUAL_SET_DRIFT")

 if not str(v5.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"): errors.append("V5_NOT_INDEPENDENT_PASS")
 vv=v5.get("verified") if isinstance(v5.get("verified"),Mapping) else {}
 if vv.get("typed_case_count")!=192 or vv.get("explicit_scope_case_count")!=24: errors.append("V5_TYPED_SCOPE_MATRIX_DRIFT")
 if vv.get("identifiable_or_interaction_rescue_count")!=144: errors.append("V5_RESCUE_COUNT_DRIFT")
 if "SCOPE" not in set(vv.get("mechanism_classes") or []): errors.append("V5_SCOPE_NOT_FIRST_CLASS")
 if vv.get("hidden_intervention_state_candidate_visible") is not False: errors.append("V5_HIDDEN_INTERVENTION_LEAK")
 if vv.get("drop_provenance_mutation_killed") is not True: errors.append("V5_PROVENANCE_COUNTEREXAMPLE_NOT_KILLED")
 if vv.get("unfalsifiable_output_injection_killed") is not True: errors.append("V5_UNFALSIFIABLE_OUTPUT_COUNTEREXAMPLE_NOT_KILLED")
 if set(v5.get("exact_residuals_addressed") or [])!=EXPECTED_RESIDUALS: errors.append("V5_DOES_NOT_ADDRESS_EXACT_V4_RESIDUALS")

 terminal={}
 for tier in ("T0","T2"):
  row=_p1_receipt(wave,tier)
  if row is None: errors.append("TERMINAL_P1_RECEIPT_MISSING:"+tier); continue
  terminal[tier]=dict(row)
  for key in ("load_bearing","direct_instrumentation_pass","parent_terminal_acceptance_pass"):
   if row.get(key) is not True: errors.append("TERMINAL_P1_RECEIPT_FAIL:"+tier+":"+key)
  for key in ("case_replaced","tuning_replay","result_to_runtime_feedback"):
   if row.get(key) is not False: errors.append("TERMINAL_P1_RECEIPT_CONTAMINATED:"+tier+":"+key)
  if row.get("candidate_visible_keys")!=["PUBLIC_TASK_PAYLOAD_ONLY"]: errors.append("TERMINAL_P1_VISIBILITY_DRIFT:"+tier)

 audit=_mutation_audit()
 if not audit["all_frozen_mutations_killed"]: errors.append("V5_DOES_NOT_KILL_ALL_FROZEN_P1_MUTATIONS")
 errors=sorted(set(errors))
 return {
  "schema":SCHEMA,
  "status":"PASS__V5_SCOPE_SUPERSET_OF_FROZEN_P1_DIRECT_PROOF_CONTRACT_SEMANTICS__THREE_SURFACES_BOUND__NO_PRIVATE_POPULATION_CLAIM__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,"errors":errors,"behavior_id":BEHAVIOR,
  "surface_count":len(surfaces),"surfaces":sorted(surfaces),
  "scope_relation":"SUPERSET_OF_FROZEN_P1_DIRECT_PROOF_CONTRACT_SEMANTICS_BOUND_TO_ALL_THREE_DECLARED_SURFACES" if not errors else "NOT_PROVED",
  "claim_bound_relations":[
   {
    "claim_id":"P1_V5_SCOPE_SUPERSET::"+surface.split("::",1)[0].replace("/","::"),
    "direct_surface":surface,
    "relation":"SUPERSET" if not errors else "NOT_PROVED",
    "witness_basis":{
     "frozen_surface_binding":P1_BINDING,
     "surface_manifest":MANIFEST,
     "frozen_direct_contract":FOUR_CONTRACTS,
     "frozen_direct_route":DIRECT_ROUTES,
     "v4_exact_residual_receipt":V4_RESIDUAL,
     "v5_independent_receipt":V5_RECEIPT,
    },
    "claim_scope":"FROZEN_P1_DIRECT_PROOF_CONTRACT_SEMANTICS_ONLY",
    "private_benchmark_population_scope_claimed":False,
   }
   for surface in sorted(surfaces)
  ],
  "private_benchmark_population_scope_claimed":False,
  "semantic_basis":{"v4_exact_residuals":sorted(EXPECTED_RESIDUALS),
                    "v5_exact_residuals_addressed":sorted(v5.get("exact_residuals_addressed") or []),
                    "frozen_check_count":len(EXPECTED_CHECKS),"frozen_mutation_count":len(EXPECTED_MUTATIONS),
                    "all_frozen_mutations_killed":audit["all_frozen_mutations_killed"]},
  "mutation_audit":audit,
  "terminal_receipts_preserved":{"T0":terminal.get("T0",{}).get("case_id"),
                                 "T2":terminal.get("T2",{}).get("case_id"),
                                 "terminal_results_replayed":0},
  "quarantine_lift_eligible":False,
  "next":"INDEPENDENTLY_VERIFY_THIS_EXACT_SCOPE_SUPERSET_VERDICT__THEN_COMPOSE_WITH_IMMUTABLE_T0_T2_TERMINAL_RECEIPTS_IN_SEPARATE_P1_RESTORATION_VERIFIER__NO_DIRECT_PROMOTION_FROM_THIS_GATE",
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False}

def main()->int:
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
