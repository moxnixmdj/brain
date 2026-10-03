from canonical.runtime.matched_scope_abductive_residual_execution_v2 import execute

out=execute()

assert out["target_count"]==8
assert out["verified_rule_count"]==8
assert len(out["primitive_residual_facts"])==16
assert out["minimum_joint_residual_size"]==16
assert out["shared_residual_groups"]==[]
assert len(out["minimum_joint_residual_sets"])==1
assert len(out["minimum_joint_residual_sets"][0])==16
for pid in (
    "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
    "RECOVERY_TERMINAL_NONINFERIOR",
    "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
):
    assert pid not in out["target_residuals"]
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print("test_matched_scope_abductive_residual_execution_v2: PASS")
