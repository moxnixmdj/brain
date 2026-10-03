from canonical.runtime.current_26_zero_reality_frontier_v1 import evaluate

def test_post_tool_discovery_frontier_exact():
 x=evaluate(); assert x["pass"] is True,x
 assert x["live_world"]=={"registry_predicates":38,"proved_predicates":12,"unresolved_predicates":26,"opus55_acceptance":"5/19_PASS__14/19_OPEN"}
 assert x["zero_reality_frontier"]["active_zero_reality_requirement_count"]==16
 assert x["zero_reality_frontier"]["active_nondominated_certificate_count"]==13
 assert x["zero_reality_frontier"]["covered_predicate_count"]==24
 assert x["zero_reality_frontier"]["primitive_zero_reality_work_units"]==30
 assert x["zero_reality_frontier"]["matched_priority_child_facts"]==16
 assert x["direct_reality_blocked_predicates"]==["FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
 assert x["fresh_reality_authority"] is False

def test_tool_discovery_removed_only_from_schedule_not_recounted():
 x=evaluate(); assert x["pass"] is True,x
 assert x["retired"]["predicate"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
 assert x["retired"]["certificate"] not in x["zero_reality_frontier"]["active_nondominated_certificate_ids"]
 assert x["retired"]["requirement"] not in x["zero_reality_frontier"]["active_required_propositions"]
 assert x["acceptance_credit_delta"]==0 and x["family_credit_delta"]==0 and x["ownership_credit_delta"]==0
