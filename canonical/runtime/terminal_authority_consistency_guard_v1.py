#!/usr/bin/env python3
"""Detect stale/contradictory terminal authority mirrors without promoting state."""
from __future__ import annotations
import json, argparse
from pathlib import Path
SCHEMA="PROJECT_BRAIN_TERMINAL_AUTHORITY_CONSISTENCY_GUARD_V1"

def evaluate(basis,gap,preq):
    errors=[]; warnings=[]
    contracts={x.get("behavior_id"):x for x in basis.get("contracts",[]) if isinstance(x,dict)}
    basis_admissible={k for k,v in contracts.items() if v.get("proof_state")=="TERMINAL_ROUTE_FROZEN_ADMISSIBLE"}
    missing={x.get("behavior_id") for x in gap.get("missing_active_contracts",[]) if isinstance(x,dict)}
    contradiction=sorted(x for x in basis_admissible if x in missing)
    if contradiction: errors.append("ADMISSIBLE_CONTRACT_MARKED_MISSING:"+",".join(contradiction))
    declared=basis.get("admissible_frozen_terminal_route_count")
    if isinstance(declared,int) and declared!=len(basis_admissible):
        errors.append(f"BASIS_ADMISSIBLE_COUNT_MISMATCH:{declared}!={len(basis_admissible)}")
    if bool(basis.get("execution_authority")) != bool(preq.get("execution_authority")):
        errors.append("EXECUTION_AUTHORITY_MISMATCH")
    if basis.get("active_contract_count") not in (None,len(contracts)):
        errors.append("ACTIVE_CONTRACT_COUNT_MISMATCH")
    if gap.get("source_bindings",{}).get("registry",{}).get("active_count") not in (None,len(contracts)):
        warnings.append("COVERAGE_GAP_REGISTRY_COUNT_DIFFERS_FROM_ACTIVE_BASIS")
    return {
      "schema":SCHEMA,
      "status":"FAIL_CLOSED_STALE_OR_CONTRADICTORY_STATE" if errors else "CONSISTENT",
      "errors":errors,"warnings":warnings,
      "basis_admissible_contracts":sorted(basis_admissible),
      "coverage_gap_missing_contracts":sorted(x for x in missing if x),
      "execution_authority":False,
      "terminal_credit_delta":0,
      "fresh_terminal_evidence_consumed":0,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("basis",type=Path); ap.add_argument("gap",type=Path); ap.add_argument("preq",type=Path)
    ns=ap.parse_args()
    load=lambda p: json.loads(p.read_text(encoding="utf-8"))
    out=evaluate(load(ns.basis),load(ns.gap),load(ns.preq))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 1 if out["status"].startswith("FAIL_CLOSED") else 0
if __name__=="__main__": raise SystemExit(main())
