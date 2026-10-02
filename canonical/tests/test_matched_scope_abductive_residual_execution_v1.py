from canonical.runtime.matched_scope_abductive_residual_execution_v1 import execute

out = execute()

assert out["target_count"] == 11
assert out["verified_rule_count"] == 11
assert len(out["primitive_residual_facts"]) == 22
assert out["minimum_joint_residual_size"] == 22
assert out["shared_residual_groups"] == []
assert len(out["minimum_joint_residual_sets"]) == 1
assert len(out["minimum_joint_residual_sets"][0]) == 22
assert out["new_reality_units_consumed"] == 0
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print("test_matched_scope_abductive_residual_execution_v1: PASS")
