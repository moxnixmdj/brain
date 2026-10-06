from __future__ import annotations
import hashlib, json
from canonical.runtime import h100_reference_machine_u1 as u1
from canonical.runtime import h100_u1_chart_axes_text_legend_compiler_v1 as comp
from canonical.runtime import h100_u1_chart_fresh_world_generator_v1 as worldgen

PROGRAM_SHA="2baf3fa772b75730cd4aa6ffbf13f960a1a79e7139f83f3ace956f6ca7bba847"
WORLD_SHA="e9f28e6d9b369a161c804ea4413ec8289fc9b522b8a5a3b2447e0a23412af5b6"

def expected_vector(g):
    return [int(g["tick"]),int(g["legend"]),int(g["bar_count"]),*map(int,g["values"])]

def run():
    program=comp.program()
    psha=hashlib.sha256(program).hexdigest()
    if psha!=PROGRAM_SHA: raise RuntimeError("PROGRAM_HASH_MISMATCH")
    wb=worldgen.canonical_bytes()
    wsha=hashlib.sha256(wb).hexdigest()
    if wsha!=WORLD_SHA: raise RuntimeError("WORLD_HASH_MISMATCH")
    world=json.loads(wb)
    rows=[]
    for task in world["tasks"]:
        inp=comp.encode_public_input(task["public_input"])
        out=u1.run(program,inp,max_steps=200000,max_stack_depth=500,max_heap_cells=500,max_output_values=20)
        want=expected_vector(task["gold"])
        rows.append({
            "id":task["id"],
            "output":out["output"],
            "gold":want,
            "pass":out["output"]==want,
            "steps":out["steps"]
        })
    return {
      "schema":"PROJECT_BRAIN_H100_U1_CHART_FRESH_RESULT_V1",
      "program_bytes":len(program),
      "program_bits":8*len(program),
      "program_sha256":psha,
      "world_sha256":wsha,
      "passed":sum(r["pass"] for r in rows),
      "total":len(rows),
      "max_steps":max(r["steps"] for r in rows),
      "learned_bits":0,
      "rows":rows
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
