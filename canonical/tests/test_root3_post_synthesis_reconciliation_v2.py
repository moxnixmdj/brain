from canonical.runtime.root3_post_synthesis_reconciliation_verifier_v2 import evaluate

def test_post_synthesis_root3_state():
    out=evaluate()
    assert out["pass"] is True,out
    assert out["live_root3_predicate_count"]==10
    assert out["matched_scope_target_count"]==7
    assert out["minimum_event_class_count"]==3
    assert out["synthesis_root3"] is False
    assert out["acceptance_credit_delta"]==0
    assert out["fresh_reality_authority"] is False
