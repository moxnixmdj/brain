from canonical.runtime.p3_contract_native_provenance_gate_verifier_v1 import verify


def test_p3_contract_native_provenance_gate_is_executable_and_fail_closed():
    out = verify()
    assert out["pass"] is True, out
    assert out["base_cases_checked"] == 2500
    assert out["seed80_required_support_repaired"] is True
    assert set(out["mutation_results"]) == {"missing", "mismatch", "orphan"}
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
