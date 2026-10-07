import json
from pathlib import Path
from canonical.runtime.terminal_frontier_factorizer_v5 import factorize, META_REFINEMENTS

ROOT=Path(__file__).resolve().parents[2]

def verify():
    d=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V10.json").read_text())
    t=d["current_truth"]; f=factorize()
    errors=[]
    if (t["independent_terminal_conjuncts"],t["direct_result_conjuncts"],t["structural_independent_conjuncts"])!=(20,15,5):
        errors.append("COUNT")
    if t["meta_context_refinements"]!=8 or len(META_REFINEMENTS)!=8:
        errors.append("META")
    if f["independent_truth_count"]!=20 or f["direct_result_count"]!=15 or f["structural_independent_count"]!=5:
        errors.append("FACTOR")
    if "ABSOLUTE_D_L2" not in d["normal_form"]["D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"]["absolute_gate_rule"]:
        errors.append("L2")
    if d["accounting"]["terminal_credit_delta"]!=0:
        errors.append("CREDIT")
    return {"pass":not errors,"errors":errors,"terminal_credit_delta":0}
