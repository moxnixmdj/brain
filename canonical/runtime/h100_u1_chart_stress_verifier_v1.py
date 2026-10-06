from __future__ import annotations
import hashlib,json
from canonical.runtime import h100_reference_machine_u1 as u1
from canonical.runtime import h100_u1_chart_axes_text_legend_compiler_v1 as comp
from canonical.runtime import h100_u1_chart_stress_world_v1 as stress

PROGRAM_SHA="2baf3fa772b75730cd4aa6ffbf13f960a1a79e7139f83f3ace956f6ca7bba847"

def expected_vector(g):
    return [int(g["tick"]),int(g["legend"]),int(g["bar_count"]),*map(int,g["values"])]

def run():
    p=comp.program()
    if hashlib.sha256(p).hexdigest()!=PROGRAM_SHA: raise RuntimeError("PROGRAM_HASH_MISMATCH")
    world=stress.generate()
    rows=[]
    for task in world["tasks"]:
        try:
            inp=comp.encode_public_input(task["public_input"])
            out=u1.run(p,inp,max_steps=200000,max_stack_depth=500,max_heap_cells=500,max_output_values=20)
            got=out["output"]; err=None; steps=out["steps"]
        except Exception as exc:
            got=None; err=type(exc).__name__+":"+str(exc); steps=None
        want=expected_vector(task["gold"])
        rows.append({"id":task["id"],"output":got,"gold":want,"pass":got==want,"exception":err,"steps":steps})
    return {
      "schema":"PROJECT_BRAIN_H100_U1_CHART_STRESS_RESULT_V1",
      "program_bytes":len(p),
      "passed":sum(r["pass"] for r in rows),
      "total":len(rows),
      "rows":rows
    }
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
