from __future__ import annotations
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_TERMINAL_STRIKE_COMPILER_V1"

def _load(root:Path, rel:str)->dict[str,Any]:
    return json.loads((root/rel).read_text(encoding="utf-8"))

def compile_strike(root:Path)->dict[str,Any]:
    auth=_load(root,"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
    q=_load(root,"canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json")
    gen=_load(root,"canonical/governance/DECISION_RELEVANT_ADMISSION_GENERATOR_CLOSURE_THEOREM_20261007_V1.json")
    comp=_load(root,"canonical/governance/SELECTED_COVER_COMPLEMENT_UNSAT_NORMAL_FORM_20261007_V1.json")
    rt=_load(root,"canonical/governance/TERMINAL_EXECUTION_ROOT_20261007_V1.json")
    live=auth.get("live_truth",{})
    open_ids=list(q.get("independent_open_obligations",[]))
    routes=[]

    routes.append({
      "id":"FULL_SCOPE_DB_COVER",
      "closed": bool(live.get("current_U_empty_proved") or live.get("complete_selected_context_ABC_closed")),
      "missing":[] if live.get("current_U_empty_proved") else [
        "SCOPE_COMPLETE_PROOF_THAT_S_TRACE_SUBSET_OR_EQUAL_D_B"
      ],
      "max_discharge":len(open_ids),
    })
    routes.append({
      "id":"TARGET_ESCAPE_NONOCCUPANCY",
      "closed": bool(rt.get("current_truth",{}).get("current_evidence_proves_not_X")),
      "missing":[] if rt.get("current_truth",{}).get("current_evidence_proves_not_X") else [
        "MINIMUM_POLICY_CHANGING_TARGET_FACT_OR_TARGET_FREE_NONOCCUPANCY_PROOF"
      ],
      "max_discharge":len(open_ids),
    })
    gt=gen.get("current_truth",{})
    gm=[]
    if not gt.get("decision_relevant_generator_basis_complete"): gm.append("GENERATOR_BASIS_SCOPE_COMPLETENESS")
    if not gt.get("all_generator_base_regions_covered"): gm.append("ALL_GENERATOR_BASE_REGIONS_COVERED")
    if not gt.get("all_primitive_transforms_abc_preserving"): gm.append("ALL_PRIMITIVE_TRANSFORMS_ABC_PRESERVING")
    if not gt.get("generator_closure_equals_useful_trace_scope"): gm.append("GENERATOR_CLOSURE_EQUALS_S_TRACE")
    routes.append({"id":"GENERATOR_CLOSURE_SCOPE_COMPLETE","closed":not gm,"missing":gm,"max_discharge":len(open_ids)})

    ct=comp.get("current_truth",{})
    cm=[]
    if not ct.get("residual_complement_unsat_proved"): cm.append("RESIDUAL_COMPLEMENT_R_UNSAT")
    if not ct.get("deployed_real_selected_cover_complete"): cm.append("SELECTED_COVER_COMPLETE")
    routes.append({"id":"SELECTED_COVER_COMPLEMENT_UNSAT","closed":not cm,"missing":cm,"max_discharge":len(open_ids)})

    actions=[]
    for r in routes:
        if r["closed"]: continue
        actions.append({
          "route_id":r["id"],
          "potential_discharge":r["max_discharge"],
          "work_only":r["missing"],
          "forbid_generic_detours":True,
        })

    return {
      "schema":SCHEMA,
      "pass":True,
      "terminal":bool(live.get("terminal")),
      "open_independent_obligation_count":len(open_ids),
      "open_independent_obligations":open_ids,
      "global_routes":routes,
      "dispatch":actions,
      "single_live_primitive":"ESCAPE_POLICY_ADEQUACY",
      "cancel_if_any_global_route_closes":True,
      "next_after_global_close":"FREEZE_CREDITED_ROUTES__RECOMPUTE_D__DONOR_INDEPENDENCE__CLEAN_ROOM__TERMINAL_REDUCER",
      "terminal_credit":False,
    }

if __name__=="__main__":
    import sys
    root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
    print(json.dumps(compile_strike(root),indent=2,sort_keys=True))
