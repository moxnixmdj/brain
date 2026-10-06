from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import h100_reference_machine_u3_v1 as u3

ROOT=Path(__file__).resolve().parents[2]
PROGRAM=ROOT/"canonical/governance/H100_U3_BAR_GEOMETRY_PROGRAM_PRECOMMIT_V1.json"
HOLDOUT=ROOT/"canonical/governance/H100_U3_BAR_FRESH_HOLDOUT_MATERIALIZED_V1.json"

def run():
    p=json.loads(PROGRAM.read_text())
    h=json.loads(HOLDOUT.read_text())
    program=bytes.fromhex(p["program"]["hex"])
    if hashlib.sha256(program).hexdigest()!=p["program"]["sha256"]:
        raise ValueError("PROGRAM_HASH_MISMATCH")
    rows=[]
    for c in h["cases"]:
        z=u3.execute(program,c["input"],step_limit=50000,memory_cells=2048,stack_limit=128,output_limit=64)
        got=list(z["output"])
        rows.append({"id":c["id"],"pass":got==c["gold"],"steps":z["steps"],"got":got,"gold":c["gold"]})
    return {
      "schema":"PROJECT_BRAIN_H100_U3_BAR_FRESH_MATERIALIZED_VERIFIER_V1",
      "status":"PASS__10_OF_10_FRESH" if all(x["pass"] for x in rows) and len(rows)==10 else "FAIL__FRESH_RESIDUAL",
      "passed":sum(x["pass"] for x in rows),
      "total":len(rows),
      "program_bytes":len(program),
      "program_bits":8*len(program),
      "program_sha256":hashlib.sha256(program).hexdigest(),
      "max_steps":max(x["steps"] for x in rows),
      "mean_steps":sum(x["steps"] for x in rows)/len(rows),
      "rows":rows
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
