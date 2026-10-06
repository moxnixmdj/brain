from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1 as u1

ROOT=Path(__file__).resolve().parents[2]
PROG=ROOT/"canonical/governance/H100_U1_PIECEWISE_CALIBRATION_PROGRAM_PRECOMMIT_V1.json"
HOLD=ROOT/"canonical/governance/H100_U1_PIECEWISE_CALIBRATION_HOLDOUT_V1.json"
AUDIT=ROOT/"canonical/governance/H100_U1_PIECEWISE_CALIBRATION_MIDDLE_BRANCH_AUDIT_V1.json"

def run():
    p=json.loads(PROG.read_text())
    h=json.loads(HOLD.read_text())
    a=json.loads(AUDIT.read_text())
    program=bytes.fromhex(p["raw_program_hex"])
    rows=[]
    for source,cases in [("COMMIT_DERIVED_HOLDOUT",h["cases"]),("COVERAGE_AUDIT",a["cases"])]:
        for c in cases:
            out=u1.run(program,[int(c["x"])],max_steps=1000,max_stack_depth=100,max_heap_cells=10,max_output_values=2)
            got=out["output"]
            rows.append({
                "source":source,
                "x":int(c["x"]),
                "gold":int(c["y"]),
                "output":got,
                "pass":got==[int(c["y"])],
                "steps":out["steps"],
            })
    return {
        "schema":"PROJECT_BRAIN_H100_U1_PIECEWISE_CALIBRATION_RESULT_V1",
        "program_bytes":len(program),
        "program_bits":8*len(program),
        "random_holdout_passed":sum(r["pass"] for r in rows if r["source"]=="COMMIT_DERIVED_HOLDOUT"),
        "random_holdout_total":sum(1 for r in rows if r["source"]=="COMMIT_DERIVED_HOLDOUT"),
        "coverage_audit_passed":sum(r["pass"] for r in rows if r["source"]=="COVERAGE_AUDIT"),
        "coverage_audit_total":sum(1 for r in rows if r["source"]=="COVERAGE_AUDIT"),
        "all_pass":all(r["pass"] for r in rows),
        "max_steps_observed":max(r["steps"] for r in rows),
        "target_adapted_persistent_bits_upper_bound":8*len(program),
        "learned_bits":0,
        "rows":rows,
    }
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
