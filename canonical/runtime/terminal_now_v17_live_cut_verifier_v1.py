from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUT = "canonical/governance/TERMINAL_NOW_V17_LIVE_CUT_20261007_V1.json"
EXPECTED = {
    "canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json": "e77766459fecbc15c983cbe5a26175101b94d5f7",
    "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json": "8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/FINANCE_DIRECT_ROUTE_SOURCE_COVERAGE_TRUTH_REPAIR_20261007_V1.json": "b760bdf4b68c51261d6513b232baaf5339089c8f",
    "canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json": "2ae349caea470c716fcb48c23984d7603c963d6b",
    "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_SOUNDNESS_REDUCTION_20261007_V1.json": "1259a3e3e6872d5355d92f19e9e3df217bdc254d",
}

def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def verify() -> dict:
    errors: list[str] = []
    for path, expected in EXPECTED.items():
        if not (ROOT / path).is_file():
            errors.append("SOURCE_MISSING:" + path)
        elif blob(path) != expected:
            errors.append("SOURCE_DRIFT:" + path)

    cut = load(CUT)
    v16 = load("canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json")
    db = load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    finance = load("canonical/governance/FINANCE_DIRECT_ROUTE_SOURCE_COVERAGE_TRUTH_REPAIR_20261007_V1.json")
    two = load("canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json")

    if v16["current_truth"].get("known_sound_D_B_region_count") != 9:
        errors.append("V16_EXPECTED_STALE_REGION_COUNT_NOT_FOUND")
    if db["saturation_result"].get("known_D_B_region_count") != 10:
        errors.append("TEN_REGION_SATURATION_NOT_BOUND")
    if cut["current_truth"].get("known_sound_D_B_region_count") != 10:
        errors.append("CUT_REGION_COUNT_NOT_REPAIRED")

    stale = "OPEN_NO_VERIFIED_OPERATIVE_FINANCE_JUDGMENT_CONFIGURATION"
    finance_rows = {x["id"]: x for x in v16.get("named_surviving_abc_residuals", [])}
    if finance_rows.get("FINANCE_UNCOVERED_OBJECTIVE_DIRECT_PROOF", {}).get("current_state") != stale:
        errors.append("V16_EXPECTED_STALE_FINANCE_STATE_NOT_FOUND")
    if finance["truth_repair"].get("delete_stale_statement") != "NO_VERIFIED_BRAIN_OWNED_OPERATIVE_FINANCE_JUDGMENT_CONFIGURATION_FOR_THE_TWO_UNCOVERED_LEAVES":
        errors.append("FINANCE_STALE_DELETE_NOT_BOUND")
    replacement = finance["truth_repair"].get("replacement_statement", "")
    if "SOURCE_TO_TYPED_SEMANTIC_AND_EVIDENCE_COVERAGE" not in replacement:
        errors.append("FINANCE_REPLACEMENT_NOT_BOUND")

    residual_ids = {v["residual_id"] for v in two["leaf_reduction"].values()}
    expected_residual_ids = {
        "FINANCE_RULE_SEMANTIC_BINDING_AND_CONSEQUENCE_COMPLETENESS",
        "FINANCE_DOCUMENT_SEMANTIC_GRAPH_AND_DECISION_RELEVANCE_COMPLETENESS",
    }
    if residual_ids != expected_residual_ids:
        errors.append("FINANCE_TWO_LEAF_RESIDUAL_SET_DRIFT")
    if set(cut["finance_live_cut"].get("residuals", [])) != expected_residual_ids:
        errors.append("CUT_FINANCE_RESIDUAL_SET_MISMATCH")

    if cut["current_truth"].get("abc_closed") is not False:
        errors.append("ABC_FALSELY_CLOSED")
    if cut["current_truth"].get("d_finality_closed") is not False:
        errors.append("D_FALSELY_CLOSED")
    if cut["current_truth"].get("terminal") is not False:
        errors.append("TERMINAL_FALSELY_PROMOTED")
    if cut["terminal_now_theorem"].get("conclusion") != "COMPLETE_SELECTED_CONTEXT_ABC_IS_NOT_PROVED_FROM_CURRENT_BOUND_BYTES__THEREFORE_TERMINAL_TRUE_IS_NOT_CURRENTLY_SOUND":
        errors.append("TERMINAL_NOW_CONCLUSION_DRIFT")
    if cut["accounting"].get("terminal_credit_delta") != 0:
        errors.append("NONZERO_TERMINAL_CREDIT")

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_NOW_V17_LIVE_CUT_VERIFY_V1",
        "status": "PASS__LIVE_STALE_FIELDS_REPAIRED__REAL_TERMINAL_CUT_PRESERVED" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "known_sound_D_B_region_count": 10 if not errors else None,
        "finance_residual_count": 2 if not errors else None,
        "abc_closed": False,
        "d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
