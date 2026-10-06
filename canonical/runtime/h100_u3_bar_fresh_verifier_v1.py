from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import h100_reference_machine_u3_v1 as u3
from canonical.runtime import h100_u3_bar_fresh_holdout_generator_v1 as gen

ROOT=Path(__file__).resolve().parents[2]
PROGRAM_PRE=ROOT/"canonical/governance/H100_U3_BAR_GEOMETRY_PROGRAM_PRECOMMIT_V1.json"

def run():
    pre=json.loads(PROGRAM_PRE.read_text())
    program=bytes.fromhex(pre["program"]["hex"])
    if hashlib.sha256(program).hexdigest()!=pre["program"]["sha256"]:
        raise ValueError("PROGRAM_HASH_MISMATCH")
    if len(program)!=pre["program"]["bytes"]:
        raise ValueError("PROGRAM_SIZE_MISMATCH")
    rows=[]
    for case in gen.generate(10):
        r=u3.execute(
            program,
            case["input"],
            step_limit=50000,
            memory_cells=2048,
            stack_limit=128,
            output_limit=64,
        )
        got=list(r["output"])
        rows.append({
            "id":case["id"],
            "pass":got==case["gold"],
            "got":got,
            "gold":case["gold"],
            "steps":r["steps"],
            "height":case["height"],
            "width":case["width"],
        })
    passed=sum(x["pass"] for x in rows)
    return {
        "schema":"PROJECT_BRAIN_H100_U3_BAR_FRESH_VERIFICATION_V1",
        "status":"PASS__10_OF_10_FRESH" if passed==10 else "FAIL__FRESH_RESIDUAL",
        "passed":passed,
        "total":10,
        "program_bytes":len(program),
        "program_bits":8*len(program),
        "program_sha256":hashlib.sha256(program).hexdigest(),
        "max_steps":max(x["steps"] for x in rows),
        "mean_steps":sum(x["steps"] for x in rows)/len(rows),
        "rows":rows,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
