from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1 as u1
from canonical.runtime import h100_u1_chart_axes_text_legend_compiler_v1 as comp

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_RAW_CHART_AXES_TEXT_LEGEND_HOLDOUT_PRECOMMIT_V1.json"

def expected_vector(gold):
    return [int(gold["tick"]),int(gold["legend"]),int(gold["bar_count"]),*map(int,gold["values"])]

def run():
    spec=json.loads(PRE.read_text())
    program=comp.program()
    rows=[]
    for t in spec["tasks"]:
        inp=comp.encode_public_input(t["public_input"])
        out=u1.run(program,inp,max_steps=200000,max_stack_depth=500,max_heap_cells=500,max_output_values=20)
        want=expected_vector(t["gold"])
        rows.append({"id":t["id"],"output":out["output"],"gold":want,"pass":out["output"]==want,"steps":out["steps"]})
    return {"program_bytes":len(program),"passed":sum(r["pass"] for r in rows),"total":len(rows),"rows":rows,"NO_CREDIT":"DISCOVERY_HOLDOUT_USED_DURING_COMPILATION"}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
