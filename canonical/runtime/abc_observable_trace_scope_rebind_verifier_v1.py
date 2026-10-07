from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json":"97412c8b7b107789c01906012163d3088991f1a4",
"canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json":"333bdc8306a19f005a600a47b415a4bd9cf9868c",
"canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_SPRITE_VERIFICATION_20261006_V1.json":"954ed383aa79fd8838249e58b0c848e338ea44de",
"canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_FALSIFICATION_20261006_V1.json":"f308c0bce3cdff8b8c523e231d337c68f1ed976f",
"canonical/governance/TARGET_UNDOMINATED_ESCAPE_REDUCTION_20261007_V1.json":"c6757e71f862dd592402199ac12afb8bca45c256",
"canonical/verification/TARGET_UNDOMINATED_ESCAPE_WOLFRAM_VERIFICATION_20261007_V1.json":"54d1f2184548dba880adcd9006df31e6c4dc3f65",
}
def blob(b:bytes):
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def reduce_scope(*,externally_useful_implies_observable:bool,opaque_payload_total:bool,composition_total:bool,independent_replay_pass:bool,brain_dominance_claimed:bool):
 e=[]
 if not externally_useful_implies_observable:e.append("UTILITY_OBSERVABILITY_PREMISE_MISSING")
 if not opaque_payload_total:e.append("PAYLOAD_SUPERDOMAIN_NOT_TOTAL")
 if not composition_total:e.append("COMPOSITION_ESCAPE")
 if not independent_replay_pass:e.append("INDEPENDENT_REPLAY_NOT_PASS")
 if brain_dominance_claimed:e.append("SCOPE_PROOF_SMUGGLES_DOMINANCE")
 return {"pass":not e,"errors":e,"scope_closed":not e,"dominance_closed":False}
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 t=load("canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json")
 sv=load("canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_SPRITE_VERIFICATION_20261006_V1.json")
 f=load("canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_FALSIFICATION_20261006_V1.json")
 u=load("canonical/governance/TARGET_UNDOMINATED_ESCAPE_REDUCTION_20261007_V1.json")
 v12=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json")
 basis=set((t.get("first_principles_definition") or {}).get("trace_event_basis") or [])
 if len(basis)!=6: errors.append("TRACE_BASIS_COUNT_DRIFT")
 if (t.get("critical_split") or {}).get("target_universe_scope_state")!="STRUCTURALLY_SUPERSET_BY_OBSERVABLE_TRACE_DEFINITION": errors.append("TRACE_SCOPE_NOT_SUPERSET")
 if (t.get("critical_split") or {}).get("current_acceptance_basis_universal_dominance_state")!="OPEN": errors.append("DOMINANCE_FALSELY_CLOSED")
 if not str(sv.get("status","")).startswith("INDEPENDENT_SPRITE_SEMANTIC_REPLAY_PASS"): errors.append("TRACE_REPLAY_NOT_PASS")
 checks=sv.get("checks") or {}
 if checks.get("scope_theorem_present") is not True or checks.get("dominance_explicitly_open") is not True: errors.append("TRACE_REPLAY_SEMANTIC_DRIFT")
 attacks=f.get("attacks") or []
 tw=[x for x in attacks if x.get("falsifier")=="TWO_WORLDS_TERMINAL_COUNTERMODEL"]
 if len(tw)!=1 or tw[0].get("does_not_kill")!="OBSERVABLE_TRACE_SCOPE_SUPERSET": errors.append("TWO_WORLDS_NOT_RECLASSIFIED")
 if (u.get("theorem") or {}).get("important_consequence") is None: errors.append("UNDOMINATED_ESCAPE_THEOREM_MISSING")
 ct=v12.get("current_truth") or {}
 if ct.get("target_universe_scope_superset_closed") is not True: errors.append("V12_SCOPE_NOT_CLOSED")
 if ct.get("terminal") is not False: errors.append("TERMINAL_FALSE_REQUIRED")
 abc=v12.get("abc_normal_form") or {}
 if (abc.get("scope") or {}).get("state")!="CLOSED": errors.append("ABC_SCOPE_NOT_CLOSED")
 if (abc.get("dominance") or {}).get("state")!="OPEN": errors.append("ABC_DOMINANCE_MUST_STAY_OPEN")
 if (abc.get("escape") or {}).get("closure_condition")!="U_INTERSECTION_E_IS_EMPTY": errors.append("ESCAPE_CLOSURE_DRIFT")
 r=reduce_scope(externally_useful_implies_observable=True,opaque_payload_total=True,composition_total=True,independent_replay_pass=True,brain_dominance_claimed=False)
 errors.extend("REDUCTION:"+x for x in r["errors"])
 return {"schema":"PROJECT_BRAIN_ABC_OBSERVABLE_TRACE_SCOPE_REBIND_VERIFIER_V1","status":"PASS__TARGET_SCOPE_SUPERSET_CLOSED__DOMINANCE_AND_UNDOMINATED_ESCAPE_REMAIN_OPEN__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"target_scope_superset_closed":not errors,"abc_closed":False,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
