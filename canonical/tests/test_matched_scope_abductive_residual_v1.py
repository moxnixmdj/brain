from __future__ import annotations
import json
from pathlib import Path

from canonical.runtime.abductive_residual_theorem_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

inp = json.loads((ROOT / "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V1.json").read_text(encoding="utf-8"))
sub = json.loads((ROOT / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json").read_text(encoding="utf-8"))
refinement = json.loads((ROOT / "canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json").read_text(encoding="utf-8"))
activation = json.loads((ROOT / "canonical/governance/ABDUCTIVE_RESIDUAL_THEOREM_ACTIVATION_V1.json").read_text(encoding="utf-8"))

assert refinement["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert refinement["exact_brain_blobs"]["canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json"] == "89162df13fae66edabaa53ac9c8d95a88829e3ec"
assert activation["status"].startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS")
assert all(
    edge["receipt"] == "canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
    for edge in inp["implications"]
)

out = evaluate(inp)

assert out["status"] == "EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED", out
assert out["target_count"] == 11
assert out["verified_rule_count"] == 11
assert len(out["primitive_residual_facts"]) == 22
assert out["shared_residual_groups"] == []
assert out["minimum_joint_residual_size"] == 22
assert len(out["minimum_joint_residual_sets"]) == 1

expected_union = set()
expected_by_target = {}
for cert in sub["certificates"]:
    target = cert["target_predicates"][0]
    req = sorted(cert["requires"])
    expected_by_target[target] = req
    expected_union.update(req)

assert set(out["minimum_joint_residual_sets"][0]) == expected_union
assert set(out["primitive_residual_facts"]) == expected_union

for target, req in expected_by_target.items():
    row = out["target_residuals"][target]
    assert row["reachable"] is True
    assert row["minimum_residual_size"] == 2
    assert row["minimum_residual_sets"] == [req]
    assert row["facts_in_every_minimum_residual"] == req

assert out["new_reality_units_consumed"] == 0
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print("test_matched_scope_abductive_residual_v1: PASS")
