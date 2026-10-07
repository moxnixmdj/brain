from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V4.json"
BASE = "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json"
EXPECTED = {
    BASE: "8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json": "0ccc3ecbdbf2636b8f1e7f0daf959a48350cb82e",
    "canonical/verification/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_INDEPENDENT_VERIFICATION_20261007_V1.json": "f3e86554f87868587d4ce3f58f97714b2dbe4672",
    "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json": "28692768a21e95b51e847417cf5ba2343587e4aa",
    "canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json": "aefee446782989518c9794db1e73909bd3c4f55c",
}
NEW_IDS = {
    "PROFESSIONAL_ARTIFACT_P2_INFO_SAFE_V2_ALL_GENERATED_CASES",
    "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT",
}

def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def verify():
    errors = []
    for rel, want in EXPECTED.items():
        p = ROOT / rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:" + rel)
            continue
        if blob(p.read_bytes()) != want:
            errors.append("SOURCE_DRIFT:" + rel)

    base = load(BASE)
    new = load(MANIFEST)
    base_ids = [x["id"] for x in base.get("known_D_B_regions", [])]
    new_ids = [x["id"] for x in new.get("known_D_B_regions", [])]
    if len(base_ids) != 10 or len(set(base_ids)) != 10:
        errors.append("BASE_TEN_INVALID")
    if len(new_ids) != 12 or len(set(new_ids)) != 12:
        errors.append("NEW_TWELVE_INVALID")
    if not set(base_ids).issubset(new_ids):
        errors.append("BASE_REGION_LOST")
    if set(new_ids) - set(base_ids) != NEW_IDS:
        errors.append("DELTA_NOT_EXACTLY_TWO_CERTIFIED_REGIONS")

    p2 = load("canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json")
    p2v = load("canonical/verification/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_INDEPENDENT_VERIFICATION_20261007_V1.json")
    consequence = p2.get("abc_consequence") or {}
    if not (
        consequence.get("selected_cell_scope_complete") is True
        and consequence.get("direct_e2e") is True
        and consequence.get("proposed_D_B_region") == "PROFESSIONAL_ARTIFACT_P2_INFO_SAFE_V2_ALL_GENERATED_CASES"
        and consequence.get("artifact_family_closed") is False
    ):
        errors.append("P2_UNIVERSAL_CELL_INVALID")
    if not (
        (p2v.get("wolfram") or {}).get("result", {}).get("All16ScoreCasesEqual") is True
        and "NO_ABC_CLOSURE" in (p2v.get("hard_nonclaims") or [])
    ):
        errors.append("P2_UNIVERSAL_VERIFICATION_INVALID")

    u = load("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json")
    uv = load("canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json")
    prop = u.get("selected_property_cell") or {}
    effect = u.get("v14_effect") or {}
    if not (
        prop.get("brain_value") == 1
        and prop.get("top_value") == 1
        and effect.get("K_c_minus") == "EMPTY_BECAUSE_BRAIN_VALUE_IS_THE_TOP_ELEMENT_ONE"
        and effect.get("add_to_D_B") == "ONLY_THIS_EXACT_FROZEN_T1_PROFESSIONAL_UNSUPPORTED_CONTENT_PROPERTY_CELL"
    ):
        errors.append("UNSUPPORTED_CONTENT_CELL_INVALID")
    if not (uv.get("wolfram_result") is True and "GLOBAL_ABC_OR_D" in (uv.get("not_verified") or [])):
        errors.append("UNSUPPORTED_CONTENT_VERIFICATION_INVALID")

    sat = new.get("saturation_result") or {}
    if sat.get("base_region_count") != 10 or sat.get("added_region_count") != 2 or sat.get("known_D_B_region_count") != 12:
        errors.append("COUNT_DRIFT")
    if sat.get("coverage_measure_not_claimed") is not True or sat.get("regions_may_overlap") is not True:
        errors.append("OVERCLAIM_GUARD_MISSING")
    if new.get("accounting", {}).get("fresh_reality_units_consumed") != 0:
        errors.append("FRESH_REALITY_NONZERO")
    if new.get("accounting", {}).get("terminal_credit_delta") != 0:
        errors.append("TERMINAL_CREDIT_NONZERO")

    return {
        "schema": "PROJECT_BRAIN_V16_DB_EXISTING_EVIDENCE_SATURATION_VERIFIER_V4",
        "status": "PASS__TWELVE_SOUND_CACHED_D_B_REGIONS__EXACT_PLUS_TWO__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "base_region_count": 10,
        "new_region_count": 12 if not errors else None,
        "delta_region_count": 2 if not errors else None,
        "delta_region_ids": sorted(NEW_IDS) if not errors else None,
        "abc_closed": False,
        "d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
