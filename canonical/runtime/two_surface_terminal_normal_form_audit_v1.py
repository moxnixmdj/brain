from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.terminal_frontier_factorizer_v5 import ATOMIC, META_REFINEMENTS

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def audit():
    th=load("canonical/governance/TWO_SURFACE_TERMINAL_NORMAL_FORM_THEOREM_20261007_V1.json")
    protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    basis=load("canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json")
    errors=[]
    rows=th["burden_cells"]
    ids=[x["id"] for x in rows]
    if len(ids)!=len(set(ids)):
        errors.append("DUPLICATE_BURDEN_CELL")
    if set(ids)!=set(ATOMIC):
        errors.append("BURDEN_CELL_SET_MISMATCH")
    protocol_families={x["family"] for x in protocols["protocols"]}
    roles={x["id"] for x in basis["functional_basis"]}
    for row in rows:
        if row["family"] not in protocol_families:
            errors.append("UNKNOWN_PROTOCOL_FAMILY:"+row["id"])
        if not row["roles"] or not set(row["roles"])<=roles:
            errors.append("UNKNOWN_OR_EMPTY_ROLE:"+row["id"])
    if len(th["top_level_surfaces"])!=2:
        errors.append("TOP_LEVEL_SURFACE_COUNT")
    if len(META_REFINEMENTS)!=8:
        errors.append("META_REFINEMENT_COUNT")
    if th["accounting"]["terminal_credit_delta"]!=0:
        errors.append("NONZERO_CREDIT")
    return {
      "status":"PASS__20_CELLS_MAP_TO_ABC__2_TOP_LEVEL_SURFACES" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "burden_cell_count":len(ids),
      "meta_refinement_count":len(META_REFINEMENTS),
      "top_level_surface_count":len(th["top_level_surfaces"]),
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(audit(),indent=2,sort_keys=True))
