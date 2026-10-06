from __future__ import annotations
import json, math
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1 as u1

ROOT=Path(__file__).resolve().parents[2]
PROG=ROOT/"canonical/governance/H100_U1_RUNTIME_GLYPH_ATLAS_LOOKUP_PROGRAM_PRECOMMIT_V1.json"
WORLD=ROOT/"canonical/governance/H100_GLYPH_SEMANTICS_RUNTIME_INFORMATION_WORLD_V1.json"

def run():
    p=json.loads(PROG.read_text())
    w=json.loads(WORLD.read_text())
    program=bytes.fromhex(p["raw_program_hex"])
    atlas=[]
    for pat,dig in zip(w["patterns"],w["digits"]):
        atlas.extend([int(pat),int(dig)])
    rows=[]
    for pat,dig in zip(w["patterns"],w["digits"]):
        inp=[int(pat),*atlas]
        out=u1.run(program,inp,max_steps=1000,max_stack_depth=100,max_heap_cells=10,max_output_values=2)
        rows.append({"pattern":pat,"gold_digit":dig,"output":out["output"],"pass":out["output"]==[dig],"steps":out["steps"]})
    worlds=int(w["no_atlas_condition"]["hidden_worlds_for_target_semantics"])
    return {
        "schema":"PROJECT_BRAIN_H100_GLYPH_SEMANTICS_RUNTIME_INFORMATION_RESULT_V1",
        "program_bytes":len(program),
        "program_bits":8*len(program),
        "atlas_entries":len(w["patterns"]),
        "atlas_runtime_integer_values":2*len(w["patterns"]),
        "with_atlas_passed":sum(r["pass"] for r in rows),
        "with_atlas_total":len(rows),
        "with_atlas_max_steps":max(r["steps"] for r in rows),
        "with_atlas_world_specific_persistent_bits":0,
        "without_atlas_hidden_worlds":worlds,
        "without_atlas_uniform_exact_success_upper_bound_zero_world_bits":1/worlds,
        "without_atlas_fixed_length_world_specific_bits_for_all_worlds":math.ceil(math.log2(worlds)),
        "rows":rows,
    }
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
