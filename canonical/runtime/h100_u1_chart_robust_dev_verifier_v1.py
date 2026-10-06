from __future__ import annotations
import json
from canonical.runtime import h100_reference_machine_u1 as u1
from canonical.runtime import h100_u1_chart_robust_compiler_v1 as comp
from canonical.runtime import h100_u1_chart_stress_world_v1 as stress

def want(g): return [int(g["tick"]),int(g["legend"]),int(g["bar_count"]),*map(int,g["values"])]

def run():
    p=comp.program(); rows=[]
    for task in stress.generate()["tasks"]:
        inp=comp.encode_public_input(task["public_input"])
        try:
            out=u1.run(p,inp,max_steps=20000000,max_stack_depth=1000,max_heap_cells=1000,max_output_values=20)
            got=out["output"]; err=None; steps=out["steps"]
        except Exception as exc:
            got=None; err=type(exc).__name__+":"+str(exc); steps=None
        rows.append({"id":task["id"],"pass":got==want(task["gold"]),"output":got,"gold":want(task["gold"]),"error":err,"steps":steps})
    return {"program_bytes":len(p),"passed":sum(r["pass"] for r in rows),"total":len(rows),"rows":rows,"NO_CREDIT":"DEVELOPED_AFTER_STRESS"}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
