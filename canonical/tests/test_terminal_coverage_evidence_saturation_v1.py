from canonical.runtime.terminal_coverage_evidence_saturation_v1 import (
    coverage_projection_truth_status,
    empty_evidence_countermodel,
)


def test_empty_evidence_j0_does_not_prove_no_j_certificate_can_be_bound():
    out = empty_evidence_countermodel()
    assert out["baseline_j_count"] == 0
    assert out["with_j_count"] == 1
    assert out["baseline_route"] != "J"
    assert out["with_complete_j_route"] == "J"
    assert out["countermodel_valid"] is True
    assert out["empty_evidence_proves_no_j_certificate_exists"] is False


def test_missing_scan_state_keeps_projection_partial():
    out = coverage_projection_truth_status(
        evidence_by_item={},
        scan_state_by_item={},
    )
    assert out["scan_complete_for_all_32"] is False
    assert len(out["missing_scan_items"]) == 32
    assert out["negative_route_counts_are_exhaustive_current_evidence_claim"] is False
    assert out["status"] == "BASELINE_OR_PARTIAL_EVIDENCE_PROJECTION"


def test_only_all_saturated_states_authorize_current_evidence_negative_interpretation():
    baseline = coverage_projection_truth_status(
        evidence_by_item={},
        scan_state_by_item={},
    )["compiled"]
    states = {
        item: "SATURATED_NO_BOUND_CERTIFICATE"
        for item in baseline["classifications"]
    }
    out = coverage_projection_truth_status(
        evidence_by_item={},
        scan_state_by_item=states,
    )
    assert out["scan_complete_for_all_32"] is True
    assert out["negative_route_counts_are_exhaustive_current_evidence_claim"] is True
    assert out["status"] == "SATURATED_CURRENT_EVIDENCE_PROJECTION"
    assert out["terminal_credit"] is False
