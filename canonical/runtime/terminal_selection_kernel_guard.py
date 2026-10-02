from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any

KERNEL="canonical/governance/GLOBAL_TERMINAL_SELECTION_KERNEL_V1.json"
GLOBAL="canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json"
FIELDS=("global_freeze_order","seed_policy","information_boundary","route_specific_requirements","portfolio_multiplexing")

def evaluate(root:Path)->dict[str,Any]:
    errors=[]
    try:
        kernel=json.loads((root/KERNEL).read_text(encoding="utf-8"))
        current=json.loads((root/GLOBAL).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"status":"FAIL_CLOSED","errors":["READ:"+type(exc).__name__]}
    for field in FIELDS:
        if kernel.get(field)!=current.get(field):
            errors.append("SEMANTIC_PROJECTION_DRIFT:"+field)
    if kernel.get("dependency_rule")!="ROUTE_PROOFS_BIND_THIS_KERNEL_FOR_SELECTION_SEMANTICS__MUTABLE_GLOBAL_ROUTE_COUNTS_FROZEN_ROUTE_REGISTRIES_AND_DERIVED_SCOREBOARDS_ARE_NOT_BEHAVIOR_RELEVANT_ROUTE_DEPENDENCIES":
        errors.append("DEPENDENCY_RULE")
    return {
      "schema":"PROJECT_BRAIN_GLOBAL_TERMINAL_SELECTION_KERNEL_GUARD_V1",
      "status":"PASS__SELECTION_SEMANTICS_EQUIVALENT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "execution_authority":False,
      "promotion_authority":False,
      "terminal_results_observed":0,
      "fresh_terminal_evidence_consumed":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
    }

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("root",type=Path,nargs="?",default=Path("."));a=ap.parse_args()
    out=evaluate(a.root);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
