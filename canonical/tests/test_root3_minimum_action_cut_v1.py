from canonical.runtime.root3_minimum_action_cut_v1 import evaluate

def test_current_root3_minimum_action_cut():
 out=evaluate()
 assert out["status"].startswith("PASS__"),out
 assert out["live_root3_predicates"]==11
 assert out["formal_population_identities"]==4
 assert out["synthesis_scope_relations"]==1
 assert out["composition_open_interfaces"]==8
 assert out["matched_scope_targets_shared_wave"]==8
 assert out["direct_oracle_leaves"]==4
 assert out["event_class_count"]==3
 assert out["currently_runnable_event_count"]==0
 assert out["new_reality_units_consumed"]==0
 assert out["fresh_reality_authority"] is False
