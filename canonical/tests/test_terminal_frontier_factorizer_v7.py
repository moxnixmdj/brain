from canonical.runtime.terminal_frontier_factorizer_v7 import factorize

def test_v7_truth_repaired_projection():
    x = factorize()
    assert x["top_level_terminal_predicate_count"] == 2
    assert x["top_level_terminal_predicates"] == [
        "COMPLETE_SELECTED_CONTEXT_ABC",
        "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",
    ]
    assert x["abc_refinement_partition_count"] == 19
    assert x["direct_result_refinement_count"] == 15
    assert x["structural_abc_refinement_count"] == 4
    assert x["sound_db_certificate_record_count"] == 15
    assert x["u_cardinality_known"] is False
    assert x["u_cardinality"] is None
    assert x["u_empty_proved"] is False
    assert "REFINEMENT_COUNTS_AND_DB_RECORD_COUNTS_MUST_NOT_BE_USED_AS_U_CARDINALITY" == x["critical_truth"]
    assert x["terminal_credit_delta"] == 0
