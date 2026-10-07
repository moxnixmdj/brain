from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_LITERAL_ALL_META_FINALITY_ABSORPTION_VERIFIER_V1"

EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json": "09f11461c7aa1ee7719409723726712f68d03da8",
    "canonical/governance/ABC_OBSERVABLE_TRACE_SCOPE_REBIND_20261007_V1.json": "c93145d33d0db802f301f987cf196be1bb479197",
    "canonical/governance/LITERAL_ALL_CAPABILITY_UNIVERSE_EXHAUSTIVENESS_THEOREM_V1.json": "2ee40ca11e58f19b34fc8cd1bb849a4b4cf08ec1",
    "canonical/governance/LITERAL_ALL_META_FINALITY_ABSORPTION_INTO_UNIVERSAL_ABC_20261007_V1.json": "05c3fb75f533a080005aa1fa1c27a2290510019d",
}

def blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def verify() -> dict:
    errors = []
    for path, expected in EXPECTED.items():
        actual = blob_sha(path)
        if actual != expected:
            errors.append(f"DRIFT:{path}:{actual}")

    v15 = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json")
    scope = load("canonical/governance/ABC_OBSERVABLE_TRACE_SCOPE_REBIND_20261007_V1.json")
    literal = load("canonical/governance/LITERAL_ALL_CAPABILITY_UNIVERSE_EXHAUSTIVENESS_THEOREM_V1.json")
    repair = load("canonical/governance/LITERAL_ALL_META_FINALITY_ABSORPTION_INTO_UNIVERSAL_ABC_20261007_V1.json")
    v17 = load("canonical/governance/TERMINAL_NOW_V17_LIVE_REBASE_20261007_V1.json")

    expected_preds = [
        "COMPLETE_SELECTED_CONTEXT_ABC",
        "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",
    ]
    if v15["current_truth"]["independent_top_level_terminal_predicates"] != expected_preds:
        errors.append("V15_TOP_LEVEL_PREDICATES")
    if v15["current_truth"]["independent_top_level_terminal_predicate_count"] != 2:
        errors.append("V15_TOP_LEVEL_COUNT")
    if scope["rebind"]["coverage_statement"] != "U_SUBSET_OR_EQUAL_S_TRACE":
        errors.append("SCOPE_SUPERSET_NOT_CLOSED")
    if scope["rebind"]["remaining_equivalent_condition"] != "U_INTERSECTION_E_IS_EMPTY":
        errors.append("ABC_ESCAPE_CONDITION")
    if "CURRENT_19_FAMILY_MAPPING_WITHOUT_PROOF_THAT_ITS_UNION_CONTAINS_U" not in literal["non_sufficient_routes"]:
        errors.append("FINITE_ENUMERATION_GUARD_MISSING")
    if repair["truth_effect"]["terminal_predicates_after_repair"] != expected_preds:
        errors.append("REPAIR_PREDICATE_SET")
    if repair["truth_effect"]["terminal_after_repair"] is not False:
        errors.append("REPAIR_FALSE_TERMINAL_REQUIRED")
    if v17["meta_finality_frontier"].get("independent_terminal_predicate") is not False:
        errors.append("V17_META_STILL_INDEPENDENT")
    if v17["truth_rebase"].get("literal_all_guard_absorbed_into_complete_selected_context_ABC") is not True:
        errors.append("V17_ABSORPTION_NOT_BOUND")
    if v17["truth_rebase"].get("complete_selected_context_ABC_closed") is not False:
        errors.append("V17_ABC_OVERCLAIM")
    if v17["truth_rebase"].get("D_finality_closed") is not False:
        errors.append("V17_D_OVERCLAIM")
    if v17["truth_rebase"].get("terminal") is not False:
        errors.append("V17_TERMINAL_OVERCLAIM")

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "errors": errors,
        "independent_terminal_predicates": expected_preds if not errors else None,
        "duplicate_meta_gate_deleted": not errors,
        "finite_enumeration_guard_preserved": not errors,
        "terminal": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
