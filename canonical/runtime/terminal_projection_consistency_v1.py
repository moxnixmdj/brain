from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATHS={
 "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
 "closure":"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
 "matrix":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
 "atomic_bindings":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
 "delegation_acceptance":"canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "recovery_acceptance":"canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
def _load(p): return json.loads((ROOT/p).read_text())
def _sha(p):
 d=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def evaluate_documents(a,c,m,e,d,r,shas=None):
 err=[]
 sat=e.get("saturation",{}); proved=sat.get("proved_predicate_count"); unresolved=sat.get("unresolved_predicate_count")
 cs=c.get("opus55_acceptance_summary",{}); closed=cs.get("calibrated_family_count"); opened=cs.get("pending_family_count")
 accepted=set(cs.get("calibrated_families",[])); pending=set(cs.get("pending_families",[]))
 if proved+unresolved!=38: err.append("ATOMIC_COUNTS")
 if len([x for x in e.get("claims",[]) if x.get("state")=="PROVED"])!=proved: err.append("PROVED_CLAIMS")
 if closed+opened!=19 or len(accepted)!=closed or len(pending)!=opened or accepted&pending: err.append("FAMILY_PARTITION")
 if c.get("opus55_acceptance_summary",{}).get("atomic_predicates")!={"proved":proved,"unresolved":unresolved,"total":38}: err.append("CLOSURE_ATOMIC")
 if a.get("truth",{}).get("opus55_acceptance")!=f"{closed}/19_PASS__{opened}/19_OPEN": err.append("AUTH_ACCEPTANCE")
 if a.get("truth",{}).get("achieved") is not False: err.append("AUTH_ACHIEVED")
 af=a.get("atomic_acceptance_frontier",{})
 if (af.get("proved"),af.get("unresolved"),af.get("total"))!=(proved,unresolved,38): err.append("AUTH_ATOMIC")
 ms=m.get("postwave_acceptance_summary",{})
 if (ms.get("calibrated_family_count"),ms.get("pending_acceptance_family_count"))!=(closed,opened): err.append("MATRIX_COUNTS")
 if set(ms.get("calibrated_families",[]))!=accepted: err.append("MATRIX_FAMILIES")
 ma=ms.get("atomic_acceptance",{})
 if (ma.get("proved"),ma.get("unresolved"),ma.get("total"))!=(proved,unresolved,38): err.append("MATRIX_ATOMIC")
 if not str(d.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS") or "SUBAGENT_DELEGATION_AND_COORDINATION" not in accepted: err.append("DELEGATION")
 rr=r.get("verified_result",{}).get("after",{})
 if not str(r.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"): err.append("RECOVERY_RECEIPT")
 if (rr.get("proved_atomic"),rr.get("unresolved_atomic"),rr.get("accepted_families"),rr.get("open_families"))!=(proved,unresolved,closed,opened): err.append("RECOVERY_STATE")
 if "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY" not in accepted: err.append("RECOVERY_FAMILY")
 if shas is not None:
  src=a.get("sources",{})
  for k,p in {"terminal_closure_manifest":PATHS["closure"],"ownership_matrix":PATHS["matrix"],"acceptance_predicate_evidence_bindings_reconciled":PATHS["atomic_bindings"],"delegation_acceptance_reduction":PATHS["delegation_acceptance"],"recovery_acceptance_integrator_verification":PATHS["recovery_acceptance"]}.items():
   row=src.get(k,{})
   if row.get("path")!=p or row.get("git_blob_sha")!=shas[p]: err.append("SOURCE:"+k)
 return {"schema":"PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V4","status":"PASS" if not err else "FAIL_CLOSED","pass":not err,"errors":sorted(set(err)),"acceptance_closed_families":closed,"acceptance_open_families":opened,"accepted_families":sorted(accepted),"atomic_predicates_proved":proved,"atomic_predicates_unresolved":unresolved,"terminal_goal_achieved":False,"capability_credit_delta":0,"family_credit_delta":0,"promotion_authority":False,"execution_authority":False}
def evaluate_live():
 x={k:_load(v) for k,v in PATHS.items()}; s={v:_sha(v) for v in PATHS.values()}
 return evaluate_documents(x["authority"],x["closure"],x["matrix"],x["atomic_bindings"],x["delegation_acceptance"],x["recovery_acceptance"],s)
def main():
 o=evaluate_live(); print(json.dumps(o,indent=2,sort_keys=True)); return 0 if o["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
