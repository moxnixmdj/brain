import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
S={
 "v5":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V5.json","8f18c4165e927a15fdb7d348d3edfde93b0cedaa"),
 "pb":("canonical/governance/EVALUATOR_PULLBACK_DOMINANCE_THEOREM_20261007_V1.json","5febbf7c34368dcce354da44201436a49f87c108"),
 "pv":("canonical/verification/EVALUATOR_PULLBACK_DOMINANCE_VERIFICATION_20261007_V1.json","05d66cf13843578c9a34c929ba1c32509f075c44"),
}
def blob(p):
 b=(R/p).read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p):return json.loads((R/p).read_text())
def verify():
 e=[f"DRIFT:{k}" for k,(p,h) in S.items() if blob(p)!=h]
 if e:return {"pass":False,"errors":e,"terminal":False}
 v5=load(S["v5"][0]);pb=load(S["pb"][0]);pv=load(S["pv"][0])
 if v5["current_truth"]["open_truth_obligations"]!=29:e.append("TRUTH_COUNT")
 if "pullback" not in pb["theorem"]:e.append("PULLBACK_THEOREM")
 if not pv["verified"]["source_pullback_dominance_implies_target_dominance"]:e.append("PULLBACK_VERIFY")
 return {"pass":not e,"errors":e,"open_truth_obligations":29 if not e else None,
 "accepted_families":5 if not e else None,"open_families":14 if not e else None,
 "C_primitive_certificate":"EVALUATOR_PULLBACK_PLUS_HARD_CONSTRAINT_PREIMAGE",
 "terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 o=verify();print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
