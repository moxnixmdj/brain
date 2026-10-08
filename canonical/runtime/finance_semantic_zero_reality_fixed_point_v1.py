from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_FINANCE_SEMANTIC_ZERO_REALITY_FIXED_POINT_VERIFY_V1"
FIXED="canonical/governance/FINANCE_SEMANTIC_ZERO_REALITY_FIXED_POINT_20261008_V1.json"
EXPECTED={
"canonical/governance/FINANCE_POLICY_ADEQUACY_DECISION_QUOTIENT_20261008_V1.json":"39f659583562ae950202a982880de3a1bf9a7ff2",
"canonical/governance/FINANCE_DIRECT_ROUTE_SOURCE_COVERAGE_TRUTH_REPAIR_20261007_V1.json":"b760bdf4b68c51261d6513b232baaf5339089c8f",
"canonical/governance/FINANCE_PROOF_CARRYING_SOURCE_SEMANTIC_GATE_20261007_V1.json":"f43ddf33a63659ce6a853b9f3d75de0b7b1e5d66",
"canonical/governance/FINANCE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_20261007_V1.json":"d9453733ac28a205305129ac7b80e6ea1b692815",
"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V1.json":"423e0d2186974dfe335b6366c73621bab1dfc039",
}

def _blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def evaluate()->dict:
    errors=[]
    for rel,want in EXPECTED.items():
        path=ROOT/rel
        if not path.is_file():
            errors.append("SOURCE_MISSING:"+rel)
            continue
        got=_blob(path)
        if got!=want:
            errors.append("SOURCE_DRIFT:"+rel+":"+got)
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":errors,"terminal_credit_delta":0}

    quotient=_load("canonical/governance/FINANCE_POLICY_ADEQUACY_DECISION_QUOTIENT_20261008_V1.json")
    counter=_load("canonical/governance/FINANCE_DIRECT_ROUTE_SOURCE_COVERAGE_TRUTH_REPAIR_20261007_V1.json")
    source_gate=_load("canonical/governance/FINANCE_PROOF_CARRYING_SOURCE_SEMANTIC_GATE_20261007_V1.json")
    shared=_load("canonical/governance/FINANCE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_20261007_V1.json")
    root2=_load("canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V1.json")
    fixed=_load(FIXED)

    eq=str((quotient.get("definitions") or {}).get("equivalence") or "")
    if "A_i_EQUALS_A_j" not in eq:
        errors.append("POLICY_QUOTIENT_EQUIVALENCE_DRIFT")
    remaining=str(quotient.get("remaining_boundary") or "")
    if "SURVIVING_INTERPRETATION" not in remaining and "DIRECT_END_TO_END_ADEQUACY" not in remaining:
        errors.append("POLICY_QUOTIENT_REMAINING_BOUNDARY_DRIFT")

    falsified=(counter.get("proof") or {}).get("universal_adequacy_falsified") or []
    joined=" ".join(str(x) for x in falsified)
    if "A_TWO_WORLD_COUNTERMODEL_EXISTS" not in joined:
        errors.append("TWO_WORLD_COUNTERMODEL_MISSING")
    if "PROTOCOL ACCEPTANCE DIFFERS" not in joined:
        errors.append("COUNTERMODEL_POLICY_RELEVANCE_MISSING")

    residual=(source_gate.get("remaining_finance_direct_residual") or {})
    if residual.get("id")!="SOUND_SOURCE_GROUNDED_SEMANTIC_INTERPRETATION_OR_EQUIVALENT_DIRECT_END_TO_END_ADEQUACY":
        errors.append("SOURCE_GATE_RESIDUAL_DRIFT")

    open_semantics=(shared.get("surviving_semantic_boundary") or {}).get("not_yet_universally_owned") or []
    if not open_semantics:
        errors.append("SHARED_SEMANTIC_RESIDUAL_UNEXPECTEDLY_EMPTY")
    shared_theorem=str((shared.get("theorem") or {}).get("statement") or "")
    if "DIRECT_END_TO_END_CERTIFICATE" not in shared_theorem:
        errors.append("SHARED_E2E_ESCAPE_ROUTE_MISSING")

    finance=(root2.get("current_cell_classifications") or {}).get("FINANCE_SEMANTIC_ADEQUACY_TAIL") or {}
    if finance.get("state")!="ZERO_REALITY_ACTIVE":
        errors.append("ROOT2_FINANCE_PRESTATE_DRIFT")
    if "DIRECT_E2E_CERTIFICATE_SEARCH" not in str(finance.get("next") or ""):
        errors.append("ROOT2_FINANCE_NEXT_ROUTE_DRIFT")

    theorem=fixed.get("theorem") or {}
    conclusion=str(theorem.get("conclusion") or "")
    if "POLICY_ADEQUACY_QUOTIENT_DOES_NOT_REMOVE_THE_TWO_WORLD_COUNTERMODEL" not in conclusion:
        errors.append("FIXED_POINT_CONCLUSION_DRIFT")
    scheduler=fixed.get("scheduler_delta") or {}
    if scheduler.get("finance_semantic_adequacy_tail_state")!="EXTERNAL_REQUIRED_SLEEP":
        errors.append("FIXED_POINT_SCHEDULER_STATE_INVALID")

    return {
        "schema":SCHEMA,
        "status":"PASS__FINANCE_SEMANTIC_ZERO_REALITY_FIXED_POINT__WAKE_GATED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "two_world_countermodel_preserved_by_policy_quotient":not errors,
        "zero_reality_internal_recomputation_exhausted":not errors,
        "finance_semantic_adequacy_tail_state":"EXTERNAL_REQUIRED_SLEEP" if not errors else "UNRESOLVED",
        "root2_globally_closed":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
