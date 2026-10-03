from canonical.runtime.verify_terminal_scheduling_current_authority_v12_candidate_v1 import evaluate

def test_v12_final_pointer_exact_blob():
    x = evaluate()
    assert x["pass"] is True, x
    assert x["pointer_blob_sha"] == "bc578e6db4eedcefbed61f6860e1cc5192cf05f4"
    assert x["active_zero_reality_requirements"] == 17
    assert x["primitive_zero_reality_work_units"] == 31
    assert x["tool_discovery_retrieval_authority"] == "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
    assert x["fresh_reality_authority"] is False
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False
