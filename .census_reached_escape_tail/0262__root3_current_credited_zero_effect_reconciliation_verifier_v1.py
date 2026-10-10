from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = "canonical/governance/ROOT3_CURRENT_CREDITED_ZERO_EFFECT_RECONCILIATION_20261007_V1.json"
EXPECTED = {
    "canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_20261007_V1.json": "9fd755465ae17b19335987b78c154afa6434ab3a",
    "canonical/governance/ACCEPTED_PURE_ROUTE_EFFECT_FOOTPRINT_OUTPUT_20261007_V2.json": "0720daf2fccce24932538e6ee0cc53db3d0472da",
    "canonical/verification/ACCEPTED_PURE_ROUTE_STATIC_REACHABILITY_SPRITE_VERIFICATION_20261007_V1.json": "f51f7842346b58250a8d14c9bfbf9ef38f7179bf",
}
ROUTE_IDS = {
    "accepted.delegation",
    "accepted.exact_symbolic",
    "accepted.recovery",
    "accepted.tool_discovery",
}


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def verify() -> dict:
    errors: list[str] = []
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append("SOURCE_MISSING:" + rel)
        elif _blob(path) != expected:
            errors.append("SOURCE_DRIFT:" + rel)

    doc = _load(DOC)
    footprint = _load("canonical/governance/ACCEPTED_PURE_ROUTE_EFFECT_FOOTPRINT_OUTPUT_20261007_V2.json")
    reach = _load("canonical/verification/ACCEPTED_PURE_ROUTE_STATIC_REACHABILITY_SPRITE_VERIFICATION_20261007_V1.json")

    if footprint.get("status") != "PASS__CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILED":
        errors.append("FOOTPRINT_NOT_PASS")
    if footprint.get("credited_route_count") != 4:
        errors.append("CREDITED_ROUTE_COUNT")
    if {x.get("route_id") for x in footprint.get("credited_routes", [])} != ROUTE_IDS:
        errors.append("CREDITED_ROUTE_SET")
    if footprint.get("material_effect_count") != 0 or footprint.get("material_effect_ids") != []:
        errors.append("CURRENT_CREDITED_EFFECT_FOOTPRINT_NOT_EMPTY")
    if footprint.get("scope_complete_claim_from_receipts") is not True:
        errors.append("FOOTPRINT_SCOPE_COMPLETE_RECEIPTS_NOT_BOUND")
    if footprint.get("fail_closed_outside_footprint_required") is not True:
        errors.append("FAIL_CLOSED_OUTSIDE_FOOTPRINT_NOT_REQUIRED")

    if reach.get("result", {}).get("pass") is not True:
        errors.append("INDEPENDENT_REACHABILITY_NOT_PASS")
    if reach.get("result", {}).get("material_effect_ids") != []:
        errors.append("INDEPENDENT_REACHABILITY_EFFECTS_NONEMPTY")
    if set(reach.get("routes", {})) != ROUTE_IDS:
        errors.append("INDEPENDENT_REACHABILITY_ROUTE_SET")

    current = doc.get("current_truth", {})
    if current.get("credited_route_count") != 4:
        errors.append("DOC_ROUTE_COUNT")
    if set(current.get("credited_routes", [])) != ROUTE_IDS:
        errors.append("DOC_ROUTE_SET")
    if current.get("compiled_material_effect_count") != 0:
        errors.append("DOC_EFFECT_COUNT")
    if current.get("missing_effect_mediators_for_current_credited_route_set") != 0:
        errors.append("DOC_FALSE_MEDIATOR_GAP")
    if current.get("global_seven_effect_class_driver_totality_required_now") is not False:
        errors.append("DOC_GLOBAL_TOTALITY_NOT_DELETED")

    terminal = doc.get("terminal_effect", {})
    if terminal.get("D_finality_closed") is not False:
        errors.append("D_FALSELY_CLOSED")
    if terminal.get("complete_selected_context_ABC_closed") is not False:
        errors.append("ABC_FALSELY_CLOSED")
    if terminal.get("terminal") is not False:
        errors.append("TERMINAL_FALSELY_PROMOTED")
    if doc.get("accounting", {}).get("terminal_credit_delta") != 0:
        errors.append("NONZERO_TERMINAL_CREDIT")

    return {
        "schema": "PROJECT_BRAIN_ROOT3_CURRENT_CREDITED_ZERO_EFFECT_RECONCILIATION_VERIFY_V1",
        "pass": not errors,
        "status": "PASS__CURRENT_CREDITED_ROOT3_EFFECT_DRIVER_GAP_DELETED__FINAL_D_PRESERVED_OPEN"
        if not errors else "FAIL_CLOSED",
        "errors": errors,
        "credited_route_count": 4 if not errors else None,
        "material_effect_count": 0 if not errors else None,
        "current_effect_driver_gap": False if not errors else None,
        "D_finality_closed": False,
        "complete_selected_context_ABC_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
