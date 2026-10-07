from canonical.runtime.m0a_raw_source_generator_image_universal_verifier_v1 import verify

def test_exact_generator_image_is_exhausted():
    out = verify()
    assert out["pass"] is True, out
    assert out["domain_count"] == 11
    assert out["case_class_count"] == 8
    assert out["generator_image_pair_count"] == 88
    assert out["pair_pass_count"] == 88
    assert out["selected_cell_scope_complete"] is True
    assert out["whole_open_ended_semantic_scope_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
