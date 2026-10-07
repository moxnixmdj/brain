from canonical.runtime.current_terminal_authority_v6_verifier import verify
def test_v6():
 x=verify();assert x["pass"],x
 assert x["open_truth_obligations"]==29
 assert x["accepted_families"]==5 and x["open_families"]==14
 assert x["C_primitive_certificate"]=="EVALUATOR_PULLBACK_PLUS_HARD_CONSTRAINT_PREIMAGE"
 assert x["terminal"] is False and x["terminal_credit_delta"]==0
