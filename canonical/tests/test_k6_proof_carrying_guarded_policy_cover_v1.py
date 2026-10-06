from canonical.runtime.k6_proof_carrying_guarded_policy_cover_v1 import (
    compile_falsifiers, compile_guarded_cover
)

def test_falsifier_bundle():
    out=compile_falsifiers()
    assert out["status"]=="PASS__FINITE_GUARDED_POLICY_COVER_FALSIFIERS"
    assert out["false_positive_guard_detected"] is True
    assert out["uncovered_context_detected"] is True
    assert out["terminal_credit_delta"]==0

def test_overlapping_guards_are_safe_when_each_is_sound():
    out=compile_guarded_cover(
      contexts=("a","b"),
      policies=("p","q"),
      certified_adequate={"a":("p",),"b":("p","q")},
      guards=[
        {"id":"g_p","policy":"p","holds":{"a":True,"b":True}},
        {"id":"g_q","policy":"q","holds":{"a":False,"b":True}},
      ])
    assert out["status"]=="CERTIFIED_FINITE_GUARDED_POLICY_COVER"
    assert out["all_selected_policies_certified_adequate"] is True

def test_declared_finite_check_does_not_claim_universal_external_coverage():
    out=compile_guarded_cover(
      contexts=("a",),policies=("p",),certified_adequate={"a":("p",)},
      guards=[{"id":"g","policy":"p","holds":{"a":True}}])
    assert out["universal_beyond_declared_contexts_claimed"] is False
