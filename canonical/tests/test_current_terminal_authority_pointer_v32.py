from canonical.runtime.current_terminal_authority_pointer_v32_verifier import verify


def test_v32_exact_counts_and_regimes():
    out = verify()
    assert out["pass"], out["errors"]
    assert out["pointer_schema"] == "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V32"
    assert out["information_wakes"] == 15
    assert out["information_regimes"] == 3
    assert out["positive_reality_classes"] == 14
    assert out["execution_lanes"] == 8
    assert out["open_refinements"] == 13


def test_v32_remains_fail_closed():
    out = verify()
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
