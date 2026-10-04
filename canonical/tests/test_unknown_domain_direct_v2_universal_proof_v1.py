from canonical.runtime import unknown_domain_direct_v2_universal_proof_v1 as proof


def test_v2_universal_proof_is_revoked_by_exact_counterexample():
    out = proof.prove()
    assert out["status"] == "FAIL__V2_UNIVERSAL_CLAIM_FALSIFIED_BY_EXACT_ADD2_BINARY64_COUNTEREXAMPLE"
    assert out["counterexample"]["status"] == "COUNTEREXAMPLE_REPRODUCED__V2_UNIVERSAL_PASS_FALSE"
    assert out["counterexample"]["candidate_terminal_consequence"] != out["counterexample"]["gold_terminal_consequence"]
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in out["counterexample"]["scorer_errors"]


def test_revoked_v2_grants_no_credit():
    out = proof.prove()
    assert out["accounting"]["acceptance_credit_delta"] == 0
    assert out["accounting"]["capability_credit_delta"] == 0
    assert out["accounting"]["ownership_credit_delta"] == 0
    assert any("NO_ACCEPTANCE_PROMOTION" in x for x in out["hard_nonclaims"])
