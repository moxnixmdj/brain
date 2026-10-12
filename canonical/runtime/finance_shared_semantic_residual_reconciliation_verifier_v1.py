from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV="canonical/governance/FINANCE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json":"09f11461c7aa1ee7719409723726712f68d03da8",
 "canonical/governance/M0_GLOBAL_SEMANTIC_DECOMPOSITION_NECESSITY_FALSIFIER_20261007_V1.json":"0c02f1c3a2b4eacf9d84b1cb81c09643305c6f8a",
 "canonical/governance/V13_FINANCE_UNCOVERED_SCOPE_ROUTING_TRUTH_REPAIR_20261007_V1.json":"432e4587bffbf5dc08975ca2740457438a6cd85d",
 "canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
 "canonical/verification/DUAL_JUDGMENT_CONTROL_CURRENT_MAIN_INDEPENDENT_VERIFICATION_20261003_V1.json":"041b73f3c212d86d870554d2dc7b8ad0b691d921",
 "canonical/verification/DUAL_JUDGMENT_GENERAL_SUBSTRATE_ROLE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"047b464ff60d4eaf04c31937b1103c8bf8d678fc",
 "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
 "canonical/capabilities/opus55/DUAL_JUDGMENT_CONTROL_ENVELOPE_V1.json":"6ea46314887a59de742e56f32893de9efce1103a",
 "canonical/runtime/judgment_control_envelope_v1.py":"7bcbfc122336a63adc72b57fb0e9077c036a46e1",
 "canonical/verification/SOURCE_CONTRACT_COMPLETENESS_V2_VERIFICATION_20261002_V1.json":"dba285299fda831a8a3bd93ea10f8fb7b7a0cced",
 "canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json":"eb316b0a674a3542280c71706fffe850d22e44fa",
 "canonical/reasoning/2026-10-02_M0A_SEMANTIC_IDENTIFIABILITY_BOUNDARY_V1.json":"a8b3ca5230e8c1e73fdc0dbe0a4c5ae2a0710a6a",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
}
def blob(p:Path)->str:
 d=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def verify():
 errors=[]
 for rel,want in EXPECTED.items():
  p=ROOT/rel
  if not p.is_file(): errors.append("SOURCE_MISSING:"+rel); continue
  got=blob(p)
  if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)
 material=load("canonical/verification/DUAL_JUDGMENT_CONTROL_CURRENT_MAIN_INDEPENDENT_VERIFICATION_20261003_V1.json")
 substrate=load("canonical/verification/DUAL_JUDGMENT_GENERAL_SUBSTRATE_ROLE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 activation=load("canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 envelope=load("canonical/capabilities/opus55/DUAL_JUDGMENT_CONTROL_ENVELOPE_V1.json")
 mset=set(material.get("verified") or [])
 if "PROOF_CARRYING_CONFIGURATION_MATERIALLY_CONTROLS_FINANCE_AND_UNKNOWN_DOMAIN_TERMINAL_DECISIONS" not in mset:
  errors.append("MATERIAL_CONTROL_NOT_PROVED")
 sv=substrate.get("verified") or {}
 if sv.get("general_substrate_test_pass") is not True: errors.append("GENERAL_SUBSTRATE_NOT_PROVED")
 if sv.get("source_gate_v2_pass") is not True: errors.append("SUBSTRATE_SOURCE_GATE_NOT_PASS")
 av=activation.get("verified") or {}
 if av.get("finance_source_admitted") is not True: errors.append("FINANCE_SOURCE_NOT_ADMITTED")
 if "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS" not in set(av.get("discharged_requirements") or []):
  errors.append("FINANCE_SOURCE_REQUIREMENT_NOT_DISCHARGED")
 if envelope.get("operative_runtime")!="canonical/runtime/judgment_control_envelope_v1.py":
  errors.append("OPERATIVE_RUNTIME_DRIFT")
 if set(envelope.get("families") or [])!={"FINANCIAL_ANALYSIS","UNKNOWN_DOMAIN_ADAPTATION"}:
  errors.append("ENVELOPE_FAMILY_SET_DRIFT")
 gov=load(GOV)
 if gov.get("stale_claim_under_attack")!="NO_VERIFIED_BRAIN_OWNED_OPERATIVE_FINANCE_JUDGMENT_CONFIGURATION_FOR_THE_TWO_UNCOVERED_LEAVES":
  errors.append("STALE_CLAIM_ID_DRIFT")
 if (gov.get("falsification") or {}).get("finance_source_admitted") is not True:
  errors.append("GOV_FINANCE_ADMISSION_DRIFT")
 if "NO_CLAIM_FINANCE_UNCOVERED_SCOPE_AUDIT_IS_CLOSED" not in (gov.get("hard_nonclaims") or []):
  errors.append("CLOSURE_GUARD_MISSING")
 return {
  "schema":"PROJECT_BRAIN_FINANCE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_VERIFIER_V1",
  "status":"PASS__FINANCE_OPERATIVE_ROUTE_EXISTS__RESIDUAL_RECLASSIFIED_TO_SHARED_SEMANTIC_OR_E2E_CERTIFICATE__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,"errors":errors,
  "finance_route_exists":not errors,
  "finance_uncovered_scope_closed":False,
  "terminal_credit_delta":0,
 }
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
