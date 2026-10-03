from canonical.runtime.delegation_whole_family_ownership_reducer_v1 import evaluate
def test_delegation_whole_family_ownership_candidate():
    out=evaluate()
    assert out["pass"] is True, out
    assert out["ownership_promotion_candidate"] is True
    assert out["ownership_credit_delta"] == 0
    assert out["promotion_authority"] is False
    assert out["external_model_or_api_required"] is False
