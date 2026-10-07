from canonical.runtime.terminal_frontier_factorizer_v6 import factorize

def test_v6_counts_and_composition_derivation():
    x = factorize()
    assert x["atomic_independent_count"] == 19
    assert x["direct_result_count"] == 15
    assert x["structural_independent_count"] == 4
    assert x["derived_inside_abc_count"] == 1
    assert x["verified_independent_truth_deletions"] == 5
    assert x["route_counts"] == {"D": 15, "U": 4, "J": 0, "G": 0, "T": 0}
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" not in x["independent_obligation_interfaces"]
    assert x["derived_rules"]["COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"] == (
        "COMPLETE_SELECTED_CONTEXT_ABC__PRIMITIVE_DOMINANCE__LOCAL_C__B9_DERIVATIVE_THEOREM"
    )
    assert x["terminal_credit_delta"] == 0
