from canonical.runtime.current_26_zero_reality_frontier_v3 import evaluate
def test_current_v3():
    o=evaluate(); assert o["pass"],o
    e=o["exact_state"]
    assert (e["proved_predicates"],e["unresolved_predicates"],e["primitive_zero_reality_work_units"])==(12,26,30),o
    assert o["delta"]["primitive_work_unit_delta"]==0,o
    assert o["fresh_reality_authority"] is False,o
