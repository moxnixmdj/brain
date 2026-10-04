from canonical.runtime import livebench_union25_constrained_response_v1 as c


def test_singleton_structural_domain_and_exact_witness():
    out = c.verify()
    assert out["instruction_id"] == "detectable_format:constrained_response"
    assert out["structural_domain"] == [["detectable_format:constrained_response"]]
    assert out["witness"] == "My answer is yes."
    assert out["witness"] in out["pinned_options"]
    assert out["pointwise_claim_if_independently_verified"]["maximum_possible_pass_count"] == 1
    assert out["pointwise_claim_if_independently_verified"]["witness_pass_count"] == 1
    assert out["acceptance_credit"] is False
