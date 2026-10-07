from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

V9=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json"
GEN=ROOT/"canonical/governance/TERMINAL_GENERATOR_BASIS_CANDIDATE_20261006_V1.json"
GREC=ROOT/"canonical/governance/G_ROUTE_FIVE_GENERATOR_DOMINANCE_RECONCILIATION_20261007_V1.json"
OWN=ROOT/"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"

EXPECTED={
    V9:"1ec7f2c86534d046e51ddda00001ed287039fc0a",
    GEN:"87909e9defe4ec12627c552c80cabb873c0c5f7c",
    GREC:"2bb66217cf42c737282428e053ad42033c30811b",
    OWN:"cf736088c1ff460283f9b62d873b8e0710374e79",
}

OWNED_STRUCTURAL={
    "G1_PERSISTENT_STATE_AND_CONTINUITY",
    "G2_DELEGATION_AND_COORDINATION",
    "G3_VERIFICATION_DEBUGGING_AND_RECOVERY",
    "G4_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    "G5_EXACT_DETERMINISTIC_COMPUTATION",
}
G6="G6_TASK_CONDITIONED_JUDGMENT_PLANNING_REASONING_AND_SYNTHESIS"
G7="G7_MULTIMODAL_PERCEPTION_ACTION_AND_ARTIFACT_INTERFACE"

def _blob(path:Path)->str:
    rel=path.relative_to(ROOT).as_posix()
    cp=subprocess.run(
        ["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],
        text=True,capture_output=True,check=False,
    )
    return cp.stdout.strip() if cp.returncode==0 else ""

def _load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def compile_ledger()->dict:
    errors=[]
    for p,h in EXPECTED.items():
        got=_blob(p)
        if got!=h:
            errors.append("SOURCE_DRIFT:"+p.name+":"+(got or "MISSING"))
    if errors:
        return {
            "schema":"PROJECT_BRAIN_CURRENT_V9_ABC_OPEN_LEDGER_V1",
            "status":"FAIL_CLOSED_SOURCE_DRIFT",
            "pass":False,
            "errors":sorted(errors),
            "terminal_credit_delta":0,
        }

    v9=_load(V9)
    gen=_load(GEN)
    grec=_load(GREC)
    own=_load(OWN)

    req=list(v9["proof_surfaces"]["ABC_SELECTED_CONTEXT_COVER"]["per_selected_cell_required"])
    factor=gen["family_factorization"]
    owned_from_grec={
        row["generator"]
        for row in grec["generator_reconciliation"]
        if row["state"]=="VERIFIED_OWNED_EQUAL_OR_BETTER"
    }
    if owned_from_grec!=OWNED_STRUCTURAL:
        errors.append("OWNED_GENERATOR_SET_DRIFT")

    rows=own.get("families") or own.get("rows") or own.get("capabilities") or []
    unresolved=[
        r for r in rows
        if r.get("status")!="VERIFIED_OWNED_EQUAL_OR_BETTER"
    ]
    if len(unresolved)!=14:
        errors.append("UNRESOLVED_FAMILY_COUNT_NOT_14")

    cells=[]
    for row in unresolved:
        family=row.get("family")
        if family not in factor:
            errors.append("FAMILY_FACTOR_MISSING:"+str(family))
            continue
        fs=list(factor[family])
        structural=sorted(x for x in fs if x in OWNED_STRUCTURAL)
        unknown=sorted(x for x in fs if x not in OWNED_STRUCTURAL|{G6,G7})
        if unknown:
            errors.append("UNKNOWN_GENERATOR:"+family+":"+",".join(unknown))

        cfg=row.get("internalized_configuration")
        if isinstance(cfg,str):
            cfgs=[cfg]
        elif isinstance(cfg,list):
            cfgs=[str(x) for x in cfg]
        else:
            cfgs=[]

        cells.append({
            "cell_id":"FAMILY::"+family,
            "coarse_target_family":family,
            "coarse_cell_status":"OPEN__FAMILY_LABEL_IS_NOT_A_TERMINAL_UTILITY_QUOTIENT",
            "verified_owned_structural_generators":structural,
            "shared_semantic_frontier_required":G6 in fs,
            "interface_or_surface_suffix_binding_required":G7 in fs,
            "candidate_internalized_configuration_paths":cfgs,
            "actual_selected_route_content_addressed":False,
            "astra_or_other_donor_selected_as_brain_route":False,
            "v9_bundle":{k:False for k in req},
            "missing_v9_bundle_fields":list(req),
            "terminal_credit_delta":0,
        })

    selected_donor=any(c["astra_or_other_donor_selected_as_brain_route"] for c in cells)
    if selected_donor:
        errors.append("DONOR_SELECTED_AS_BRAIN_ROUTE")
    if len(cells)!=14:
        errors.append("CELL_COUNT_NOT_14")

    ok=not errors
    return {
        "schema":"PROJECT_BRAIN_CURRENT_V9_ABC_OPEN_LEDGER_V1",
        "status":"PASS__14_COARSE_OPEN_FAMILY_CELLS_PROJECTED_TO_OWNED_STRUCTURAL_BASIS_AND_EXACT_V9_MISSING_FIELDS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":sorted(errors),
        "authority_blob":EXPECTED[V9],
        "unresolved_family_count":len(cells),
        "owned_structural_generator_count":len(OWNED_STRUCTURAL),
        "owned_structural_generators":sorted(OWNED_STRUCTURAL),
        "generic_new_implementation_generator_required":False if ok else None,
        "cells":sorted(cells,key=lambda x:x["cell_id"]),
        "route_selection_summary":{
            "fully_content_addressed_selected_routes":sum(c["actual_selected_route_content_addressed"] for c in cells),
            "donor_routes_selected":sum(c["astra_or_other_donor_selected_as_brain_route"] for c in cells),
            "candidate_internalized_configuration_cells":sum(bool(c["candidate_internalized_configuration_paths"]) for c in cells),
        },
        "boundary":[
            "THIS_IS_A_COARSE_OPEN_LEDGER_NOT_A_TARGET_COMPLETE_SELECTED_COVER",
            "FAMILY_LABELS_ARE_NOT_TERMINAL_UTILITY_QUOTIENTS",
            "NO_LOCAL_ABC_BUNDLE_IS_CREDITED BY THIS PROJECTION",
            "CANDIDATE_INTERNALIZED_CONFIGURATION_PATHS_ARE_NOT_FULL_SELECTED_ROUTE_CERTIFICATES",
        ],
        "terminal":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=compile_ledger()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
