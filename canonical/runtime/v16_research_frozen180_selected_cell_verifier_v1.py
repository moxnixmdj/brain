from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import research_control_information_safe_candidate as candidate
from canonical.runtime import research_control_information_safe_proof as proof

ROOT=Path(__file__).resolve().parents[2]
CELL="canonical/governance/V16_RESEARCH_T3_FROZEN_180_SELECTED_CELL_20261007_V1.json"
FALSIFIER="canonical/governance/RESEARCH_CONTROL_V1_UNIVERSAL_GENERATOR_FALSIFIER_20261007_V1.json"
DELTA="canonical/governance/V16_DB_RESEARCH_FROZEN180_DELTA_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json":"e61f0544ed4b97ffe3c53d77b70b3cf067846188",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":"a7015b12f55fc971233f9fdddf59d50cfc43892b",
 "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
 "canonical/runtime/research_control_information_safe_candidate.py":"cd6bf6e4163bbba64878b856766b1af4372d68bc",
 "canonical/runtime/research_control_information_safe_proof.py":"16c47efee0e0e38f479163d1285d7079798efdaf",
 "canonical/runtime/direct_route_terminal_executors_v1.py":"28ef55db77ac81e78bd5c67e4d2b39fef131b505",
 "canonical/verification/DIRECT_ROUTE_TERMINAL_EXECUTORS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json":"a1b23e9c35a8be1dce5cec6de7f25685aca803dc",
 "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V6.json":"cdb8f76d8ee158989a51f2ebcf108c4d1847ebd3",
 "canonical/governance/V16_RESEARCH_T3_FROZEN_180_SELECTED_CELL_20261007_V1.json":"305b7e73188c735a393c201368fd96928aa74cbe",
 "canonical/governance/RESEARCH_CONTROL_V1_UNIVERSAL_GENERATOR_FALSIFIER_20261007_V1.json":"6b912eaaf5a1956f49ee9084da305797a0f83a9f",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load(rel:str):
 return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def verify():
 errors=[]
 for rel,want in EXPECTED.items():
  p=ROOT/rel
  if not p.is_file():
   errors.append("SOURCE_MISSING:"+rel); continue
  got=blob(p.read_bytes())
  if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)

 cell=load(CELL)
 sc=cell.get("selected_cell") or {}
 if sc.get("id")!="RESEARCH_T3_DIRECT_OBJECTIVE_FROZEN_180": errors.append("CELL_ID")
 if sc.get("population_complete_for_this_cell") is not True: errors.append("POPULATION_NOT_COMPLETE")
 if sc.get("open_world_research_scope_complete") is not False: errors.append("OPEN_WORLD_OVERCLAIM")
 if sc.get("brain_value")!=1 or sc.get("top_value")!=1: errors.append("TOP_VALUE_INVALID")

 bind=load("canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
 pool=bind.get("source_pool") or {}
 acc=bind.get("acceptance") or {}
 info=bind.get("information_boundary") or {}
 gates=bind.get("route_gates") or {}
 if pool.get("terminal_sample_count")!=180: errors.append("BINDING_CASE_COUNT")
 if acc.get("every_selected_case_must_pass") is not True: errors.append("BINDING_NOT_POINTWISE")
 if acc.get("hle_score_equivalence_claimed") is not False: errors.append("HLE_EQUIVALENCE_OVERCLAIM")
 if info.get("candidate_receives_hidden_oracle") is not False: errors.append("ORACLE_LEAK")
 required_gates={"candidate_package_frozen","executable_evaluator_bound","population_or_source_pool_frozen","information_boundary_frozen","post_freeze_selector_frozen","terminal_parent_binding_frozen","independent_verification_pass"}
 if any(gates.get(k) is not True for k in required_gates): errors.append("ROUTE_GATE_OPEN")

 wave=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json")
 rr=((wave.get("direct_terminal_population") or {}).get("routes") or {}).get("ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001") or {}
 if rr.get("cases")!=180 or rr.get("passes")!=180: errors.append("TERMINAL_180_NOT_ALL_PASS")
 direct=(((wave.get("reduction_input") or {}).get("wave") or {}).get("direct_results") or {}).get("ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001") or {}
 if direct.get("pass") is not True or direct.get("terminal_result") is not True: errors.append("DIRECT_RESULT_NOT_PASS")
 guards=wave.get("result_guards") or {}
 if guards.get("no_case_replacement") is not True or guards.get("no_tuning_replay") is not True or guards.get("result_to_runtime_feedback_during_wave") is not False:
  errors.append("TERMINAL_GUARD_DRIFT")

 ex=load("canonical/verification/DIRECT_ROUTE_TERMINAL_EXECUTORS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json")
 if "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001" not in (ex.get("behaviors") or []): errors.append("EXECUTOR_BEHAVIOR_NOT_VERIFIED")
 eb=ex.get("exact_brain_blobs") or {}
 if eb.get("canonical/runtime/research_control_information_safe_candidate.py")!="cd6bf6e4163bbba64878b856766b1af4372d68bc": errors.append("EXECUTOR_CANDIDATE_BINDING")
 if eb.get("canonical/runtime/research_control_information_safe_proof.py")!="16c47efee0e0e38f479163d1285d7079798efdaf": errors.append("EXECUTOR_PROOF_BINDING")
 if eb.get("canonical/runtime/direct_route_terminal_executors_v1.py")!="28ef55db77ac81e78bd5c67e4d2b39fef131b505": errors.append("EXECUTOR_RUNTIME_BINDING")

 # Exact negative canary: current generator cannot support an all-seeds theorem.
 case=proof.generate_case(7647,2)
 verdict=proof.run_episode(case,candidate.next_action)
 r3=[x for x in case["source_catalog"] if str(x.get("source_id","")).startswith("S-R3-")]
 if verdict.get("pass") is not False or verdict.get("reason")!="ACTION_BUDGET_EXHAUSTED":
  errors.append("UNIVERSAL_FALSIFIER_NOT_REPRODUCED")
 if len({x["source_id"] for x in r3})>=len(r3): errors.append("EXPECTED_ID_COLLISION_ABSENT")
 hidden=case["_oracle"]["sources"].get("S-R3-23592")
 if not isinstance(hidden,dict) or hidden.get("supports")!=[]: errors.append("COLLISION_OVERWRITE_NOT_REPRODUCED")

 delta=load(DELTA)
 rec=delta.get("reconciliation") or {}
 if rec.get("base_region_certificate_count")!=13: errors.append("BASE_13_DRIFT")
 if rec.get("distinct_added_region_certificate_count")!=1: errors.append("DELTA_COUNT_DRIFT")
 if rec.get("known_sound_region_certificate_count")!=14: errors.append("COUNT_14_DRIFT")
 if rec.get("coverage_measure_not_claimed") is not True: errors.append("COVERAGE_OVERCLAIM")
 if (delta.get("added_delta") or {}).get("region_id")!="RESEARCH_T3_DIRECT_OBJECTIVE_FROZEN_180": errors.append("DELTA_REGION_ID")

 return {
  "schema":"PROJECT_BRAIN_V16_RESEARCH_FROZEN180_SELECTED_CELL_VERIFY_V1",
  "status":"PASS__FROZEN_180_TOP_CELL__UNIVERSAL_V1_GENERALIZATION_FALSIFIED__ORTHOGONAL_DB_DELTA_14__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "frozen_180_cell_closed":not errors,
  "universal_generator_claim_allowed":False,
  "counterexample":{"seed":7647,"ordinal":2,"reason":verdict.get("reason")},
  "known_sound_region_certificate_count":14 if not errors else None,
  "abc_closed":False,
  "d_finality_closed":False,
  "terminal":False,
  "terminal_credit_delta":0,
 }
if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
