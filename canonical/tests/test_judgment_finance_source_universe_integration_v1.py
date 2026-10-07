from canonical.runtime.judgment_control_envelope_v1 import evaluate_materiality_counterfactual

def test_materiality_counterfactual_includes_closed_finance_source_universe():
    out = evaluate_materiality_counterfactual()
    assert out["pass"] is True, out
    bad = out["finance"]["configured_missing_required_exception_evidence"]
    good = out["finance"]["configured_with_recomputed_proof"]
    assert bad["accepted"] is False
    assert bad["finance_source_coverage"]["pass"] is False
    assert "FINANCE_SOURCE_COVERAGE:SOURCE_NOT_TERMINALLY_CONTRIBUTING:exception" in bad["errors"]
    assert good["accepted"] is True, good
    assert good["finance_source_coverage"]["pass"] is True
    assert good["finance_source_coverage"]["terminal_credit_delta"] == 0
