from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
G="canonical/governance/V14_FINANCE_SOURCE_ADMISSION_RECONCILIATION_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/V13_FINANCE_UNCOVERED_SCOPE_ROUTING_TRUTH_REPAIR_20261007_V1.json":"432e4587bffbf5dc08975ca2740457438a6cd85d",
 "canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json":"4211a0eee07c4758035d788c0be897d700c164cb",
 "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
 "canonical/governance/POST_SOURCE_GATE_ROOT1_RECLASSIFICATION_V1.json":"963127da19fae1f6dd7478d43076d8d9bd026c9a",
 "canonical/capabilities/opus55/DUAL_JUDGMENT_CONTROL_ENVELOPE_V1.json":"6ea46314887a59de742e56f32893de9efce1103a",
 "canonical/runtime/judgment_control_envelope_v1.py":"5ebfd1e7fa871da89ecca40ffeb8dd6575c21582",
 "canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
}
def blob(b:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 activation=load("canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 if (activation.get("verified") or {}).get("finance_source_admitted") is not True: errors.append("FINANCE_NOT_ADMITTED")
 if (activation.get("verified") or {}).get("direct_oracle_leaves_executed") is not False: errors.append("LEAF_STATE_DRIFT")
 post=load("canonical/governance/POST_SOURCE_GATE_ROOT1_RECLASSIFICATION_V1.json")
 rows=(post.get("logical_reconciliation") or {}).get("prior_candidates") or []
 f=[x for x in rows if x.get("predicate_id")=="FINANCE_UNCOVERED_SCOPE_AUDIT"]
 if len(f)!=1 or f[0].get("current_classification")!="ROOT3__DIRECT_SCOPE_EVIDENCE_RESIDUAL": errors.append("POST_SOURCE_CLASSIFICATION")
 g=load(G)
 if (g.get("reconciliation") or {}).get("finance_source_admitted") is not True: errors.append("REPAIR_ADMISSION")
 if (g.get("truth_repair") or {}).get("target_information_required") is not False: errors.append("TARGET_INFO_REINTRODUCED")
 if (g.get("truth_repair") or {}).get("new_capability_mechanism_required_now") is not False: errors.append("MECHANISM_REINTRODUCED")
 leaves=set((g.get("reconciliation") or {}).get("remaining_unexecuted_leaves") or [])
 expected_leaves={"SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE","DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"}
 if leaves!=expected_leaves: errors.append("LEAF_SET_DRIFT")
 return {"status":"PASS__FINANCE_SOURCE_ALREADY_ADMITTED__TWO_DIRECT_LEAVES_ONLY__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"finance_source_admitted":not errors,"remaining_direct_leaf_count":2 if not errors else None,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
