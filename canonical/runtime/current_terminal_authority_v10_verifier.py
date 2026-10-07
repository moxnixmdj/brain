from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V10.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json":"1ec7f2c86534d046e51ddda00001ed287039fc0a",
 "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V5.json":"a4da5b482ab01ee18715099a3bc0912443ff2032",
 "canonical/runtime/terminal_frontier_factorizer_v4.py":"bd8c89c2c18a33bfc5ba788741aff02476b6c6b1",
 "canonical/verification/TERMINAL_28_CURRENT_BASIS_WOLFRAM_VERIFICATION_20261007_V1.json":"246b1349aa734247a86e9d375f6987404646f85c",
}

def blob(rel):
    cp=subprocess.run(["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],text=True,capture_output=True,check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""

def verify():
    errors=[]
    for rel,sha in EXPECTED.items():
        if blob(rel)!=sha:
            errors.append("SOURCE_DRIFT:"+rel)
    d=json.loads(AUTH.read_text(encoding="utf-8"))
    t=d["current_truth"]
    if (t["open_truth_obligations"],t["accepted_families"],t["open_families"],t["terminal"])!=(28,5,14,False):
        errors.append("CURRENT_TRUTH_DRIFT")
    if t["route_counts"]!={"D":15,"U":13,"J":0,"G":0,"T":0}:
        errors.append("ROUTE_COUNT_DRIFT")
    if d["truth_repair"]["deleted_as_independent_truth"]!="IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS":
        errors.append("WRONG_DELETION")
    if "REMAINS_INSIDE_D_L2" not in d["truth_repair"]["preserve_absolute"]:
        errors.append("ABSOLUTE_GATE_NOT_PRESERVED")
    if d["proof_surfaces"]["D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"]["closed"] is not False:
        errors.append("D_FALSELY_CLOSED")
    if d["accounting"]["terminal_credit_delta"]!=0:
        errors.append("NONZERO_TERMINAL_CREDIT")
    return {"status":"PASS__V10_28_TRUTH_AUTHORITY_BOUND" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"terminal_credit_delta":0}

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
