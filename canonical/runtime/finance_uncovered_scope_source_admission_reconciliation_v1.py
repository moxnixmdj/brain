from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/FINANCE_UNCOVERED_SCOPE_SOURCE_ADMISSION_RECONCILIATION_20261007_V1.json"
EXPECTED={
 "canonical/governance/V13_FINANCE_UNCOVERED_SCOPE_ROUTING_TRUTH_REPAIR_20261007_V1.json":"432e4587bffbf5dc08975ca2740457438a6cd85d",
 "canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json":"4211a0eee07c4758035d788c0be897d700c164cb",
 "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
 "canonical/governance/POST_SOURCE_GATE_ROOT1_RECLASSIFICATION_V1.json":"963127da19fae1f6dd7478d43076d8d9bd026c9a",
 "canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
}
def blob(b:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("DRIFT:"+p)
 a=load("canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json")
 av=load("canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 r=load("canonical/governance/POST_SOURCE_GATE_ROOT1_RECLASSIFICATION_V1.json")
 if (a.get("resulting_direct_protocol_state") or {}).get("finance_direct_protocol")!="SOURCE_ADMITTED__FROZEN_DIRECT_ORACLE_LEAVES_REMAIN_UNEXECUTED":
  errors.append("ACTIVATION_FINANCE_STATE")
 if ((av.get("verified") or {}).get("finance_source_admitted")) is not True:
  errors.append("INDEPENDENT_FINANCE_SOURCE_NOT_ADMITTED")
 if ((av.get("verified") or {}).get("direct_oracle_leaves_executed")) is not False:
  errors.append("LEAVES_EXECUTED_STATE")
 prior=[x for x in ((r.get("logical_reconciliation") or {}).get("prior_candidates") or []) if x.get("predicate_id")=="FINANCE_UNCOVERED_SCOPE_AUDIT"]
 if len(prior)!=1 or prior[0].get("current_classification")!="ROOT3__DIRECT_SCOPE_EVIDENCE_RESIDUAL":
  errors.append("POST_GATE_CLASSIFICATION")
 return {
  "status":"PASS__FINANCE_SOURCE_ALREADY_ADMITTED__ONLY_DIRECT_LEAVES_REMAIN__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "finance_source_admitted":not errors,
  "direct_leaves_executed":False,
  "acceptance_closed":False,
  "fresh_reality_authorized":False,
  "terminal_credit_delta":0,
 }
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
