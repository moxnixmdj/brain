from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV="canonical/governance/INSTRUCTION_SCOPE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_20261007_V1.json"
EXPECTED={
 "canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json":"3ee3e56b6b235d60edba0b4666de891bf54dcbd3",
 "canonical/governance/PSTAR_INSTRUCTION_FOLLOWING_SCOPE_FIRST_APPLICATION_20261007_V1.json":"cbbfe0c588156d575763135c3decc5773a029bba",
 "canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json":"eb316b0a674a3542280c71706fffe850d22e44fa",
 "canonical/governance/M0_GLOBAL_SEMANTIC_DECOMPOSITION_NECESSITY_FALSIFIER_20261007_V1.json":"0c02f1c3a2b4eacf9d84b1cb81c09643305c6f8a",
 "canonical/runtime/instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}
def blob(p:Path)->str:
 d=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\\0"+d).hexdigest()
def load(root:Path,rel:str):
 return json.loads((root/rel).read_text(encoding="utf-8"))
def evaluate(v16,pstar,five,m0,gov):
 errors=[]
 rows=[x for x in v16.get("named_surviving_abc_residuals",[]) if x.get("id")=="INSTRUCTION_SCOPE_BOUNDARY"]
 if len(rows)!=1: errors.append("V16_INSTRUCTION_RESIDUAL_NOT_EXACTLY_ONE")
 elif rows[0].get("current_state")!="OPEN_ACCEPTANCE_PROOF_GAP_NOT_A_PROVED_PERSISTENT_CAPABILITY_GAP":
  errors.append("V16_INSTRUCTION_RESIDUAL_CLASSIFICATION_DRIFT")
 if (v16.get("current_truth") or {}).get("terminal") is not False:
  errors.append("V16_TERMINAL_BOUNDARY_DRIFT")
 if ((pstar.get("pstar_routes") or {}).get("P"))!="NOT_FORCED":
  errors.append("PSTAR_POSITIVE_P_NO_LONGER_NOT_FORCED")
 if pstar.get("verdict")!="CURRENT_EVIDENCE_IS_AN_ACCEPTANCE_PROOF_GAP_NOT_A_PROVED_PERSISTENT_CAPABILITY_GAP":
  errors.append("PSTAR_VERDICT_DRIFT")
 must=((pstar.get("decisive_positive_p_falsifier_needed") or {}).get("must_prove") or [])
 if len(must)<6: errors.append("PSTAR_POSITIVE_P_FALSIFIER_WEAKENED")
 sf=five.get("shared_frontier") or {}
 if sf.get("generic_new_implementation_generator_required") is not False:
  errors.append("SHARED_FRONTIER_NOW_REQUIRES_GENERIC_GENERATOR")
 if (five.get("role_projection") or {}).get("B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT")!="TASK_CONTRACT_CONSTRAINT_AND_TERMINAL_RELEVANCE_SEMANTICS":
  errors.append("B1_SHARED_FRONTIER_PROJECTION_DRIFT")
 te=m0.get("truth_effect") or {}
 if te.get("delete_global_prerequisite")!="M0_GENERAL_BEFORE_ABC":
  errors.append("GLOBAL_M0_NECESSITY_REOPENED")
 if "ROUTE_SEMANTICS_MUST_STILL_BE_CERTIFIED" not in te.get("preserve_route_local_requirement",""):
  errors.append("ROUTE_LOCAL_SEMANTIC_BOUNDARY_LOST")
 eff=gov.get("terminal_effect") or {}
 if any(eff.get(k) is not False for k in ("instruction_family_closed","complete_selected_context_ABC_closed","D_finality_closed","terminal")):
  errors.append("FALSE_CLOSURE_OR_TERMINAL_PROMOTION")
 acc=gov.get("accounting") or {}
 if any(acc.get(k,0)!=0 for k in ("terminal_credit_delta","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta")):
  errors.append("CREDIT_LEAK")
 if "NO_CLAIM_GENERAL_NATURAL_LANGUAGE_SEMANTICS_IS_SOLVED" not in (gov.get("hard_nonclaims") or []):
  errors.append("GENERAL_SEMANTICS_NONCLAIM_MISSING")
 return errors
def verify(root:Path=ROOT):
 errors=[]
 for rel,want in EXPECTED.items():
  p=root/rel
  if not p.is_file(): errors.append("SOURCE_MISSING:"+rel); continue
  got=blob(p)
  if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)
 if not errors:
  v16=load(root,"canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json")
  pstar=load(root,"canonical/governance/PSTAR_INSTRUCTION_FOLLOWING_SCOPE_FIRST_APPLICATION_20261007_V1.json")
  five=load(root,"canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json")
  m0=load(root,"canonical/governance/M0_GLOBAL_SEMANTIC_DECOMPOSITION_NECESSITY_FALSIFIER_20261007_V1.json")
  gov=load(root,GOV)
  errors.extend(evaluate(v16,pstar,five,m0,gov))
 return {
  "schema":"PROJECT_BRAIN_INSTRUCTION_SCOPE_SHARED_SEMANTIC_RESIDUAL_VERIFIER_V1",
  "status":"PASS__DISTINCT_INSTRUCTION_GENERIC_MECHANISM_NECESSITY_FALSIFIED__SHARED_ROUTE_LOCAL_RESIDUAL_PRESERVED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "instruction_family_closed":False,
  "terminal":False,
  "terminal_credit_delta":0,
 }
if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
