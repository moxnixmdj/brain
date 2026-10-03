from canonical.runtime.current_26_zero_reality_frontier_v2 import evaluate
def test_current():
 o=evaluate(); assert o["pass"],o
 w=o["live_world"]; assert (w["proved_predicates"],w["unresolved_predicates"])==(12,26)
 assert (w["active_zero_reality_requirements"],w["active_nondominated_certificates"],w["primitive_zero_reality_work_units"])==(16,13,30)
 assert w["matched_priority_child_facts"]==16 and w["current_normalized_targets"]==8 and w["current_normalized_witnesses"]==12
 assert w["direct_reality_eligible_predicates"]==["FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
 assert w["direct_reality_execution_authorized_now"] is False
 assert o["fresh_reality_authority"] is False and o["acceptance_credit_delta"]==0
