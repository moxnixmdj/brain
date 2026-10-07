from __future__ import annotations
import json,subprocess
from pathlib import Path
from canonical.runtime.c_acceptance_ledger_transport_gate_v1 import verify_claims

ROOT=Path(__file__).resolve().parents[2]
LEDGER="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
EXPECTED="a3fd20e58fdbd9b86278b7de0c245de3063dce27"

def blob(rel):
    cp=subprocess.run(["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],text=True,capture_output=True,check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""

def verify_current():
    got=blob(LEDGER)
    if got!=EXPECTED:
        return {"status":"FAIL_CLOSED__LEDGER_DRIFT","pass":False,"expected":EXPECTED,"actual":got,"terminal_credit_delta":0}
    doc=json.loads((ROOT/LEDGER).read_text(encoding="utf-8"))
    out=verify_claims(doc.get("claims") or [])
    if out.get("pass") is not True:
        return {"status":"FAIL_CLOSED__CURRENT_LEDGER_C_GATE","pass":False,"gate":out,"terminal_credit_delta":0}
    ok=(out["proved_count"]==14 and out["direct_count"]==14 and out["transported_count"]==0)
    return {
      "schema":"PROJECT_BRAIN_CURRENT_ACCEPTANCE_LEDGER_C_GATE_V1",
      "status":"PASS__14_CURRENT_PROVED_PREDICATES_DIRECT__ZERO_TRANSPORTED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "proved_count":out["proved_count"],
      "direct_count":out["direct_count"],
      "transported_count":out["transported_count"],
      "future_unknown_or_transport_proof_kind_fails_closed":True,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    o=verify_current();print(json.dumps(o,indent=2,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
