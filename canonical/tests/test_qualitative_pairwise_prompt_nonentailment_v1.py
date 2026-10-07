from canonical.runtime.qualitative_pairwise_prompt_nonentailment_v1 import (
    PairwiseNonentailmentError,
    evaluate,
)

def base():
    return {
        "shared_contract": {
            "prompt_blob_sha": "1"*40,
            "input_digest": "2"*64,
            "judge_identities": ["J1","J2","J3"],
            "aggregation_digest": "3"*64,
            "output_schema": "PAIRWISE_A_OR_B",
        },
        "worlds": [
            {"same_public_contract": True, "judge_semantics_bound": False, "preference": "A"},
            {"same_public_contract": True, "judge_semantics_bound": False, "preference": "B"},
        ],
    }

def test_two_world_countermodel_proves_nonentailment():
    out = evaluate(base())
    assert out["pass"] is True
    assert out["unique_preference_entailed"] is False
    assert out["exact_prompt_bytes_alone_sufficient"] is False
    assert out["terminal_credit_delta"] == 0

def test_same_preference_is_not_a_countermodel():
    d = base()
    d["worlds"][1]["preference"] = "A"
    try:
        evaluate(d)
    except PairwiseNonentailmentError as e:
        assert "DOES_NOT_FLIP" in str(e)
    else:
        raise AssertionError("expected fail closed")

def test_bound_semantics_invalidates_this_specific_countermodel_shape():
    d = base()
    d["worlds"][0]["judge_semantics_bound"] = True
    try:
        evaluate(d)
    except PairwiseNonentailmentError as e:
        assert "MUST_LEAVE_JUDGE_SEMANTICS_UNBOUND" in str(e)
    else:
        raise AssertionError("expected fail closed")

def test_world_must_share_public_contract():
    d = base()
    d["worlds"][1]["same_public_contract"] = False
    try:
        evaluate(d)
    except PairwiseNonentailmentError as e:
        assert "PUBLIC_CONTRACT_MISMATCH" in str(e)
    else:
        raise AssertionError("expected fail closed")
