from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1 as u

ROOT=Path(__file__).resolve().parents[2]
PROG=ROOT/"canonical/governance/H100_U1_FRESH_POLYNOMIAL_PROGRAM_PRECOMMIT_V2.json"
HOLD=ROOT/"canonical/governance/H100_U1_FRESH_POLYNOMIAL_HOLDOUT_V2.json"

def run():
    p=json.loads(PROG.read_text()); h=json.loads(HOLD.read_text())
    program=bytes.fromhex(p["program_hex"])
    rows=[]
    for case in h["cases"]:
        out=u.run(program,[int(case["x"])],**p["resource_limits"])
        got=out["output"]
        rows.append({"x":case["x"],"gold":case["y"],"output":got,"steps":out["steps"],"pass":got==[int(case["y"])]})
    return {
      "schema":"PROJECT_BRAIN_H100_U1_FRESH_POLYNOMIAL_RESULT_V2",
      "status":"PASS__12_OF_12_EXACT" if all(r["pass"] for r in rows) else "FAIL",
      "passed":sum(r["pass"] for r in rows),"total":len(rows),
      "raw_u1_program_bytes":len(program),"raw_u1_program_bits":8*len(program),
      "target_adapted_auxiliary_bytes":0,"learned_target_bytes":0,
      "max_steps_observed":max(r["steps"] for r in rows),
      "rows":rows
    }
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
