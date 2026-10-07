import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V17 = ROOT / "canonical/governance/TERMINAL_NOW_V17_REALITY_RECONCILIATION_20261007_V1.json"

def test_v17_reconciles_live_main_without_false_terminal_promotion():
    data = json.loads(V17.read_text(encoding="utf-8"))
    truth = data["current_truth"]
    finance = data["named_surviving_abc_residuals"]["FINANCE_UNCOVERED_OBJECTIVE_DIRECT_PROOF"]
    verdict = data["terminal_now_verdict"]

    assert truth["known_sound_D_B_region_count"] == 10
    assert truth["p2_universal_selected_cell_available"] is True
    assert finance["operative_finance_judgment_configuration_verified"] is True
    assert finance["current_gap"] == "LOAD_BEARING_SOURCE_TO_TYPED_SEMANTIC_AND_EVIDENCE_COVERAGE_OR_EQUIVALENT_SCOPE_COMPLETE_END_TO_END_CERTIFICATE"
    assert "OPEN_NO_VERIFIED_OPERATIVE_FINANCE_JUDGMENT_CONFIGURATION" not in json.dumps(data)
    assert verdict["can_truthfully_set_terminal_true_from_current_bound_evidence"] is False
    assert truth["terminal"] is False
