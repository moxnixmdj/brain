from canonical.runtime.p1_composite_mutation_adversarial_audit_v1 import audit


EXPECTED_GAPS = {
    "CHECK:FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS:EMPTY_SUPPORT_NOT_REJECTED",
    "MUTATION:DROP_PROVENANCE_OR_DEPENDENCY_EDGE:PROVENANCE_SUPPORT_DROP_NOT_REJECTED",
}


def test_p1_composite_role_audit_finds_exact_receipt_support_gap():
    out = audit()
    assert out["pass"] is False, out
    assert out["status"] == "FAIL_CLOSED__P1_COMPOSITE_ROLE_GAPS_FOUND"
    assert set(out["gaps"]) == EXPECTED_GAPS, out


def test_other_assigned_v4_obligations_are_load_bearing():
    out = audit()
    checks = out["checks"]
    assert checks["DROPPED_DEPENDENCY_EDGE_IS_REJECTED"] is True
    assert checks["MULTISTEP_CAUSAL_PREDECESSOR_IS_PRESERVED"] is True
    assert checks["IGNORED_AUTHORITY_VIOLATION_IS_REJECTED"] is True
    assert checks["NONIDENTIFIABILITY_IS_PRESERVED"] is True
    assert checks["MECHANISM_CLASS_TRACKS_VISIBLE_FAILED_CONTRACT"] is True


def test_audit_never_claims_credit_or_authority():
    out = audit()
    assert out["new_reality_units_consumed"] == 0
    assert out["terminal_results_replayed"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
