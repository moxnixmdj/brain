from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json": "09f11461c7aa1ee7719409723726712f68d03da8",
    "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json": "8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json": "28692768a21e95b51e847417cf5ba2343587e4aa",
    "canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json": "aefee446782989518c9794db1e73909bd3c4f55c",
    "canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json": "2ae349caea470c716fcb48c23984d7603c963d6b",
    "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_SOUNDNESS_REDUCTION_20261007_V1.json": "1259a3e3e6872d5355d92f19e9e3df217bdc254d",
    "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V1.json": "ecd86c13fd3f54b37fee0cb8e0fd729225feff4b",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json": "89612bd93d74ff985febb9cd8f5533e7901e91f8",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V4.json": "7c8fec5b04b75eb5a2d9861625a4c6efe59a32a5",
    "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V3.json": "fa313fd6ca68b4a00644c7d4fffca732c4c069e9",
}

def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def verify() -> dict:
    errors = []
    for path, expected in EXPECTED.items():
        p = ROOT / path
        if not p.is_file():
            errors.append("MISSING:" + path)
            continue
        actual = blob(p.read_bytes())
        if actual != expected:
            errors.append("DRIFT:" + path + ":" + actual)

    if errors:
        return {"pass": False, "errors": errors, "terminal": False}

    prior = load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    cell = load("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json")
    w = load("canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json")
    db = load("canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V1.json")
    auth = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json")
    ptr = load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V4.json")
    sched = load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V3.json")
    fin = load("canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json")
    router = load("canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_SOUNDNESS_REDUCTION_20261007_V1.json")

    prior_ids = {x["id"] for x in prior["known_D_B_regions"]}
    new_id = cell["selected_property_cell"]["id"]
    if prior["saturation_result"]["known_D_B_region_count"] != 10:
        errors.append("PRIOR_DB_COUNT")
    if new_id in prior_ids:
        errors.append("NEW_REGION_NOT_DISTINCT")
    if cell["v14_effect"]["K_c_minus"] != "EMPTY_BECAUSE_BRAIN_VALUE_IS_THE_TOP_ELEMENT_ONE":
        errors.append("NEW_REGION_NOT_TOP")
    if w.get("wolfram_result") is not True:
        errors.append("NEW_REGION_INDEPENDENT_CHECK")
    if db["promotion"]["known_sound_D_B_region_count"] != 11:
        errors.append("DB11")
    if db["promotion"]["new_region"]["id"] != new_id:
        errors.append("DB_NEW_ID")
    if auth["current_truth"]["independent_top_level_terminal_predicate_count"] != 2:
        errors.append("TOP_LEVEL_COUNT")
    if auth["current_truth"]["terminal"] is not False:
        errors.append("TERMINAL_GUARD")
    fin_ids = {v["residual_id"] for v in fin["leaf_reduction"].values()}
    if set(auth["abc_live_frontier"]["finance_residuals"]) != fin_ids:
        errors.append("FINANCE_RESIDUAL_BINDING")
    if router["theorem"]["separation"] != "ROUTER_SOUNDNESS_AND_SELECTED_COVER_COMPLETENESS_ARE_DISTINCT__A_CERTIFICATE_GATED_ROUTER_CAN_BE_SOUND_BEFORE_THE_COVER_IS_COMPLETE.":
        errors.append("ROUTER_SEPARATION")
    if auth["current_truth"]["general_router_intelligence_is_separate_global_blocker"] is not False:
        errors.append("ROUTER_BLOCKER")
    if ptr["exact_state"]["known_sound_D_B_regions_lower_bound"] != 11:
        errors.append("PTR_DB11")
    if sched.get("execution_authority") is not True:
        errors.append("EXEC_AUTH")
    if sched.get("fresh_reality_authority") is not False or sched.get("promotion_authority") is not False:
        errors.append("AUTH_BOUNDARY")
    if any(x.get("terminal_credit_delta") != 0 for x in (db["accounting"], auth["accounting"], ptr["accounting"], sched["accounting"])):
        errors.append("CREDIT")

    return {
        "pass": not errors,
        "errors": errors,
        "known_sound_D_B_regions_lower_bound": 11 if not errors else None,
        "top_level_terminal_predicates": 2 if not errors else None,
        "finance_residual_count": len(fin_ids) if not errors else None,
        "general_router_intelligence_global_blocker": False if not errors else None,
        "fresh_reality_authority": False,
        "promotion_authority": False,
        "abc_closed": False,
        "d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
