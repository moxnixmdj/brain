import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/V18_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json"
VERIFY = ROOT / "canonical/verification/V18_DB_EXISTING_EVIDENCE_SATURATION_WOLFRAM_VERIFICATION_20261007_V5.json"

def test_v18_db_twelve_region_composition_is_fail_closed():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    v = json.loads(VERIFY.read_text(encoding="utf-8"))
    ids = [r["id"] for r in m["known_D_B_regions"]]
    new_id = "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT"

    assert len(ids) == 12
    assert len(set(ids)) == 12
    assert new_id in ids
    assert m["predecessor"]["known_D_B_region_count"] == 11
    assert m["saturation_result"]["known_D_B_region_count"] == 12
    assert m["terminal_now_truth"]["abc_closed"] is False
    assert m["terminal_now_truth"]["d_finality_closed"] is False
    assert m["terminal_now_truth"]["terminal"] is False
    assert m["terminal_now_truth"]["can_truthfully_set_terminal_true_from_current_bound_evidence"] is False

    result = v["independent_provider"]["result"]
    assert result["predecessor_region_count"] == 11
    assert result["predecessor_duplicate_free"] is True
    assert result["added_region_absent_from_predecessor"] is True
    assert result["new_region_count"] == 12
    assert result["new_manifest_duplicate_free"] is True
    assert result["all_twelve_regions_true_while_abc_false_satisfiable"] is True
