from canonical.runtime.external_benchmark_dominance_compiler_v1 import evaluate

def test_external_benchmark_dominance_gate():
    o=evaluate()
    assert o["pass"],o
    assert o["current"]["proved"]==12,o
    assert o["current"]["unresolved"]==26,o
    assert o["current"]["public_fixed_bars"]==15,o
    assert o["current"]["matched_targets"]==8,o
    assert o["policy"]["custom_benchmark_creation_authorized"] is False,o
    assert o["policy"]["immediate_full_substitutions"]==0,o
    assert o["fresh_reality_authority"] is False,o
    assert o["acceptance_credit_delta"]==0,o
