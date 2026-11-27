"""Fail-closed scope transport from exact verified P1 V6 to the frozen P1 role.

This compiler proves only that the independently verified V6 forward-causal
carrier is an exact-or-stronger carrier for the frozen P1 causal-localization
role delegated by the three declared terminal surfaces. It does not claim whole
benchmark dominance, terminal acceptance, or family credit.
"""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V6_DIRECT_SURFACE_SCOPE_TRANSPORT_V1"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
ROUTE="P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF"
BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
PORTFOLIOS="canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
CONTRACTS="canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"
SUITES="canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json"
ROUTES="canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json"
V6="canonical/governance/P1_TYPED_CAUSAL_INTERVENTION_ENVELOPE_V6.json"
V6_VERIFY="canonical/verification/P1_TYPED_CAUSAL_INTERVENTION_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V5_FALSIFICATION="canonical/verification/P1_V5_PSEUDO_RESCUE_FALSIFICATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
SUPERSESSION="canonical/governance/P1_V6_VERIFIED_SUPERSESSION_OF_V5_RESCUE_V1.json"

EXPECTED_BLOBS={
 BINDING:"8703c6aa08227467a619a7ae90d0d61f8e54da39",
 PORTFOLIOS:"8b439403a05b4a912f06a8866db25f6e53b52473",
 CONTRACTS:"8c7ffe3d9ff789eddd286496f6de3ce84472c909",
 SUITES:"d8cf10dfbe041f63a43ccf43bd5dcdc8fe6f9e2b",
 ROUTES:"75cd1ad0ec0739ebd894cf6075af5837b93d83f8",
 V6:"03df530cd77cd834de94b4e3c4588008bf4a8070",
 V6_VERIFY:"1e722621db8f0f1cb3b9689e48d4bfe356dcb36e",
 V5_FALSIFICATION:"82330f9ce835ed8f31b4d758cc268297393d2443",
 SUPERSESSION:"b9f60d8b4857cb643774a5c184ee54b037664fcd",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py":"18d4de68ee8352410e986c318868642333ec085a",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py":"0f41a36e6ad16722ce05b180e036fb921a2ef886",
 "canonical/tests/test_trajectory_failure_typed_ir_v6.py":"6961f69cafd718da6dd439765a13f59ffc9790e1",
}
EXPECTED_SURFACES={
 "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF":("T0","FRONTIERCODE_V1_1"),
 "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF":("T0","CURSORBENCH_4_0"),
 "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF":("T2","RECOVERY_SCOPE_COMPOSITION"),
}
EXPECTED_NORMALIZATION="TASK_SPECIFIC_RAW_LOGS_SCREENSHOTS_TOOL_OUTPUTS_AND_ARTIFACT_EVENTS_MAY_BE_NORMALIZED_TO_THE_CANONICAL_TRAJECTORY_IR_BY_OWNED_DETERMINISTIC_OR_SEPARATELY_PROVEN_UPSTREAM_COMPONENTS"
EXPECTED_OWNED="FAILED_EXECUTION_TRAJECTORY_TO_EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_CLASS_AND_FALSIFIABLE_REPAIR_TARGET_WITH_INTERVENTION_RESCUE_EVIDENCE"
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
 "SELECT_DOWNSTREAM_SYMPTOM","SELECT_LATER_CORRELATED_STEP","IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT",
 "UNFALSIFIABLE_DIAGNOSIS","REPAIR_TARGET_WITH_NO_RESCUE","FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
 "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN","SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS","DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
}

def _blob_sha(path:str)->str:
 data=(ROOT/path).read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _load(path:str)->dict[str,Any]:
 v=json.loads((ROOT/path).read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError(path+":NOT_OBJECT")
 return v

def _one(rows:Any,pred)->Mapping[str,Any]|None:
 if not isinstance(rows,list): return None
 found=[x for x in rows if isinstance(x,Mapping) and pred(x)]
 return found[0] if len(found)==1 else None

def _surface(p:Mapping[str,Any],portfolio:str,surface:str)->Mapping[str,Any]|None:
 ps=p.get("portfolios")
 if not isinstance(ps,Mapping) or not isinstance(ps.get(portfolio),Mapping): return None
 return _one(ps[portfolio].get("surfaces"),lambda x:x.get("id")==surface)

def _transport_witnesses()->dict[str,bool]:
 cases=proof.suite_cases()
 full=all(proof.score_case(c,candidate.solve(proof.public_task(c))).get("pass") is True for c in cases)
 # visible-receipt failure must fail closed
 prov=proof.generate_case(88001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
 pp=proof.public_task(prov)
 for row in pp["task"]["trajectory"]:
  for chk in row["checks"]:
   if chk.get("pass") is False: chk["evidence"]=[]
 provenance_closed=candidate.solve(pp).get("status")=="FAIL_CLOSED"
 # downstream/later symptom diagnosis must be rejected by the frozen oracle
 delayed=proof.generate_case(88002,pattern="DELAYED",domain="CODE",kind="SCOPE")
 base=candidate.solve(proof.public_task(delayed))
 late=copy.deepcopy(base)
 late["cause_action_id"]="A4"; late["cause_action_ids"]=["A4"]; late["critical_action_id"]="A4"
 late["mechanism_classes"]=["INVARIANT"]; late["repair_targets"]=["restore:A4:INVARIANT"]
 late_rejected=proof.score_case(delayed,late).get("pass") is False
 # unfalsifiable extra claim rejected
 extra=copy.deepcopy(base); extra["diagnosis"]={"claim":"UNBOUND"}
 extra_rejected=proof.score_case(delayed,extra).get("pass") is False
 # repair with no causal effect rejected
 fake=copy.deepcopy(base); fake["repair_targets"]=["restore:A999:SCOPE"]
 fake_rejected=proof.score_case(delayed,fake).get("pass") is False and proof.execute_intervention(proof.public_task(delayed),fake).get("terminal_rescued") is False
 # ambiguity must not be coerced to a unique cause
 amb=proof.generate_case(88003,pattern="AMBIGUOUS",domain="BROWSER",kind="SCOPE")
 ao=candidate.solve(proof.public_task(amb)); forced=copy.deepcopy(ao)
 forced["status"]="IDENTIFIED"; forced["cause_action_id"]="A1"; forced["cause_action_ids"]=["A1"]; forced["critical_action_id"]="A1"
 forced.pop("candidates",None); forced.pop("information_request",None)
 forced["mechanism_classes"]=["SCOPE"]; forced["supporting_receipts"]=["x"]; forced["repair_targets"]=["restore:A1:SCOPE"]
 forced_rejected=proof.score_case(amb,forced).get("pass") is False
 # mechanism swap must be rejected
 auth=proof.generate_case(88004,pattern="SINGLE",domain="TOOL_API",kind="AUTHORITY")
 mo=candidate.solve(proof.public_task(auth)); swap=copy.deepcopy(mo); swap["mechanism_classes"]=["TOOL_CONTRACT"]
 swap_rejected=proof.score_case(auth,swap).get("pass") is False
 # dropping a load-bearing predecessor/dataflow edge changes the public causal graph and may not preserve the original proof.
 edge=proof.generate_case(88005,pattern="DELAYED",domain="FILESYSTEM",kind="DEPENDENCY")
 ep=proof.public_task(edge)
 for row in ep["task"]["trajectory"]:
  if row["action_id"]=="A2":
   row["depends_on"]=[]; row["reads"]=[]
 eo=candidate.solve(ep)
 edge_rejected=proof.score_case(edge,eo).get("pass") is False
 # symptom-only and partial interaction repairs cannot rescue.
 symptom=copy.deepcopy(base); symptom["repair_targets"]=["restore:A4:INVARIANT"]
 symptom_nonrescue=proof.execute_intervention(proof.public_task(delayed),symptom).get("terminal_rescued") is False
 inter=proof.generate_case(88006,pattern="INTERACTION",domain="ARTIFACT",kind="SCOPE")
 io=candidate.solve(proof.public_task(inter)); partial=copy.deepcopy(io); partial["repair_targets"]=partial["repair_targets"][:1]
 partial_nonrescue=proof.execute_intervention(proof.public_task(inter),partial).get("terminal_rescued") is False
 return {
  "FULL_192_FROZEN_TYPED_CROSS_PRODUCT":full,
  "DROP_PROVENANCE_OR_VISIBLE_RECEIPTS_FAILS_CLOSED":provenance_closed,
  "DOWNSTREAM_OR_LATER_SYMPTOM_DIAGNOSIS_REJECTED":late_rejected,
  "UNFALSIFIABLE_EXTRA_DIAGNOSIS_REJECTED":extra_rejected,
  "REPAIR_WITH_NO_CAUSAL_RESCUE_REJECTED":fake_rejected,
  "NONIDENTIFIABLE_FORCE_UNIQUE_REJECTED":forced_rejected,
  "MECHANISM_CLASS_SWAP_REJECTED":swap_rejected,
  "DROP_CAUSAL_PREDECESSOR_REJECTED":edge_rejected,
  "SYMPTOM_ONLY_REPAIR_NONRESCUE":symptom_nonrescue,
  "PARTIAL_INTERACTION_REPAIR_NONRESCUE":partial_nonrescue,
 }

def evaluate()->dict[str,Any]:
 errors=[]
 for path,expected in EXPECTED_BLOBS.items():
  try:
   got=_blob_sha(path)
  except Exception:
   errors.append("SOURCE_MISSING:"+path); continue
  if got!=expected: errors.append("SOURCE_BLOB_DRIFT:"+path)
 b=_load(BINDING); p=_load(PORTFOLIOS); fc=_load(CONTRACTS); suites=_load(SUITES); routes=_load(ROUTES)
 v6=_load(V6); vv=_load(V6_VERIFY); vf=_load(V5_FALSIFICATION); sup=_load(SUPERSESSION)
 if b.get("behavior_id")!=BEHAVIOR: errors.append("BINDING_BEHAVIOR_DRIFT")
 dec=b.get("decomposition") or {}
 if dec.get("owned_behavior")!=EXPECTED_OWNED: errors.append("OWNED_BEHAVIOR_DRIFT")
 if dec.get("normalization_boundary")!=EXPECTED_NORMALIZATION: errors.append("NORMALIZATION_BOUNDARY_DRIFT")
 if set(b.get("direct_surface_bindings") or [])!=set(EXPECTED_SURFACES): errors.append("DIRECT_SURFACE_SET_DRIFT")
 ev=b.get("evaluator") or {}
 if set(ev.get("required_checks") or [])!=EXPECTED_CHECKS: errors.append("FULL_REQUIRED_CHECK_SET_DRIFT")
 if set(ev.get("required_mutations") or [])!=EXPECTED_MUTATIONS: errors.append("FULL_REQUIRED_MUTATION_SET_DRIFT")
 ta=b.get("terminal_acceptance") or {}
 if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True: errors.append("SYNTHETIC_TERMINAL_FIREWALL_MISSING")
 if ta.get("parent_or_direct_surface_credit_only_for_declared_scope") is not True: errors.append("DECLARED_SCOPE_FIREWALL_MISSING")
 if b.get("terminal_results_observed")!=0: errors.append("TERMINAL_RESULT_ALREADY_OBSERVED")
 obligation=_one(fc.get("obligations"),lambda x:x.get("behavior_id")==BEHAVIOR and x.get("route_id")==ROUTE)
 if obligation is None or set(obligation.get("portfolios") or [])!={"T0","T2"}: errors.append("FROZEN_P1_OBLIGATION_DRIFT")
 suite=_one(suites.get("suites"),lambda x:x.get("id")=="P1_TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_DIRECT" and x.get("behavior_id")==BEHAVIOR)
 if suite is None: errors.append("FROZEN_P1_SUITE_MISSING")
 route=_one(routes.get("routes"),lambda x:x.get("id")=="DIRECT_TRAJECTORY_CAUSAL_CONTRACT_SUITE")
 if route is None or set(route.get("covers") or [])!={BEHAVIOR}: errors.append("CONTRACT_NATIVE_ROUTE_DRIFT")
 elif any(route.get(k) is not True for k in ("zero_cost","executable","independent_oracle","scope_mapping_frozen","contamination_boundary_frozen")) or route.get("blocked") is not False:
  errors.append("CONTRACT_NATIVE_ROUTE_NOT_ADMISSIBLE")
 surface_relations=[]
 for binding_id,(pid,sid) in EXPECTED_SURFACES.items():
  s=_surface(p,pid,sid)
  if s is None: errors.append("SURFACE_MISSING:"+binding_id); continue
  if ROUTE not in set(s.get("proof_routes") or []): errors.append("P1_ROUTE_NOT_BOUND:"+binding_id); continue
  if s.get("direct_proof_contracts")!=CONTRACTS: errors.append("DIRECT_CONTRACT_POINTER_DRIFT:"+binding_id); continue
  if s.get("evaluator")!=ROUTES: errors.append("EVALUATOR_POINTER_DRIFT:"+binding_id); continue
  surface_relations.append({"binding":binding_id,"relation":"EXACT_FROZEN_P1_ROLE_BINDING","whole_surface_claim":False})
 if v6.get("behavior_id")!=BEHAVIOR: errors.append("V6_BEHAVIOR_DRIFT")
 if not str(vv.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"): errors.append("V6_INDEPENDENT_PASS_MISSING")
 verified=vv.get("verified") or {}
 for key in ("scope_first_class","provenance_erasure_killed","unbound_output_killed","partial_interaction_repair_killed","symptom_only_repair_killed","fake_repair_string_killed","hidden_oracle_isolated","rescue_depends_on_candidate_visible_trajectory_semantics"):
  if verified.get(key) is not True: errors.append("V6_VERIFIED_PROPERTY_MISSING:"+key)
 if verified.get("cross_product_cases")!=192 or verified.get("forward_causal_rescues")!=144 or verified.get("ambiguous_abstentions")!=48:
  errors.append("V6_VERIFIED_ENVELOPE_COUNT_DRIFT")
 if (vf.get("finding") or {}).get("heterogeneous_intervention_rescue_supported") is not False: errors.append("V5_FALSIFICATION_MISSING")
 if (sup.get("supersession") or {}).get("v6_terminal_scope_transport")!="OPEN__RECOMPILE_EXACT_OR_SUPERSET_RELATION_TO_ALL_THREE_FROZEN_DIRECT_SURFACES":
  errors.append("V6_SUPERSESSION_STATE_DRIFT")
 witnesses=_transport_witnesses()
 for name,ok in witnesses.items():
  if not ok: errors.append("TRANSPORT_WITNESS_FAIL:"+name)
 if errors:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),"all_three_scope_relations_proved":False,
          "can_clear_p1_scope_quarantine":False,"terminal_surface_proof_complete":False,"new_reality_units_consumed":0,
          "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False}
 return {"schema":SCHEMA,
  "status":"PASS__EXACT_VERIFIED_V6_SUPERSETS_FROZEN_P1_ROLE_ON_ALL_THREE_DIRECT_SURFACES__V5_RESCUE_EXCLUDED__ZERO_CREDIT",
  "errors":[],"behavior_id":BEHAVIOR,"route_id":ROUTE,"surface_relations":surface_relations,
  "all_three_scope_relations_proved":len(surface_relations)==3,
  "v6_relation":"SUPERSET_OF_FROZEN_P1_ROLE_REQUIREMENTS_AT_NORMALIZED_TRAJECTORY_BOUNDARY",
  "transport_witnesses":witnesses,
  "v5_rescue_evidence_admissible":False,
  "whole_surface_superset_claim":False,"terminal_surface_proof_complete":False,"can_clear_p1_scope_quarantine":False,
  "next":"INDEPENDENTLY_VERIFY_EXACT_SCOPE_TRANSPORT_BYTES__THEN_RECOMPUTE_ONLY_P1_COMPOSITE_RESTORATION_OR_MINIMUM_IRREDUCIBLE_TERMINAL_CUT",
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False}

if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
