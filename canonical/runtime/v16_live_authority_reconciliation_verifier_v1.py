from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json": "09f11461c7aa1ee7719409723726712f68d03da8",
    "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json": "8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json": "2ae349caea470c716fcb48c23984d7603c963d6b",
    "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json": "28692768a21e95b51e847417cf5ba2343587e4aa",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json": "8a6376fdfaeeb98d77e3e4a3b362b4995afeaf49",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V4.json": "640f490bbbf28bc0e65f0cf2d96a5d75283f4b78",
    "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V3.json": "0164f4f24d57908b301537639840824e44386cd4",
}

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text())

def verify():
    errors = []
    for rel, expected in EXPECTED.items():
        p = ROOT / rel
        if not p.is_file():
            errors.append("MISSING:" + rel)
            continue
        if blob_sha(p) != expected:
            errors.append("DRIFT:" + rel)

    v16 = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json")
    ptr = load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V4.json")
    sched = load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V3.json")
    db = load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    fin = load("canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json")

    if (db.get("saturation_result") or {}).get("known_D_B_region_count") != 10:
        errors.append("DB_NOT_TEN")
    if len(db.get("known_D_B_regions") or []) != 10:
        errors.append("DB_REGION_LIST_NOT_TEN")

    truth = v16.get("current_truth") or {}
    if truth.get("independent_top_level_terminal_predicate_count") != 2:
        errors.append("TOP_LEVEL_PREDICATE_COUNT")
    if truth.get("known_sound_D_B_region_count") != 10:
        errors.append("V16_DB_COUNT")
    if truth.get("finance_remaining_route_local_semantic_binding_count") != 2:
        errors.append("V16_FINANCE_COUNT")
    if truth.get("terminal") is not False:
        errors.append("FALSE_TERMINAL_PROMOTION")

    leafs = fin.get("leaf_reduction") or {}
    ids = sorted((x.get("residual_id") for x in leafs.values() if isinstance(x, dict)))
    expected_ids = sorted([
        "FINANCE_RULE_SEMANTIC_BINDING_AND_CONSEQUENCE_COMPLETENESS",
        "FINANCE_DOCUMENT_SEMANTIC_GRAPH_AND_DECISION_RELEVANCE_COMPLETENESS",
    ])
    if ids != expected_ids:
        errors.append("FINANCE_RESIDUAL_SET")

    if (ptr.get("exact_state") or {}).get("known_cached_D_B_regions") != 10:
        errors.append("POINTER_DB_COUNT")
    if (ptr.get("exact_state") or {}).get("finance_remaining_route_local_semantic_binding_count") != 2:
        errors.append("POINTER_FINANCE_COUNT")
    if (ptr.get("exact_state") or {}).get("terminal") is not False:
        errors.append("POINTER_FALSE_TERMINAL_PROMOTION")

    world = sched.get("live_world") or {}
    if world.get("known_cached_D_B_regions") != 10:
        errors.append("SCHEDULER_DB_COUNT")
    if world.get("finance_remaining_route_local_semantic_binding_count") != 2:
        errors.append("SCHEDULER_FINANCE_COUNT")
    if world.get("terminal") is not False:
        errors.append("SCHEDULER_FALSE_TERMINAL_PROMOTION")
    if sched.get("fresh_reality_authority") is not False:
        errors.append("FRESH_REALITY_AUTHORITY_ESCALATION")
    if sched.get("promotion_authority") is not False:
        errors.append("PROMOTION_AUTHORITY_ESCALATION")

    return {
        "schema": "PROJECT_BRAIN_V16_LIVE_AUTHORITY_RECONCILIATION_VERIFY_V1",
        "pass": not errors,
        "errors": errors,
        "top_level_predicates": 2 if not errors else None,
        "known_cached_D_B_regions": 10 if not errors else None,
        "finance_route_local_semantic_bindings": 2 if not errors else None,
        "terminal": False,
        "terminal_credit_delta": 0,
        "fresh_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
