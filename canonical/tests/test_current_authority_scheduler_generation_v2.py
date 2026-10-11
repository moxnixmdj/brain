import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
scheduling = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
proof_atoms = load("canonical/governance/CANONICAL_PROOF_ATOM_BASIS_ACTIVATION_V1.json")
abductive = load("canonical/governance/ABDUCTIVE_RESIDUAL_THEOREM_ACTIVATION_V1.json")

compiled = authority["compiled_next_frontier"]
assert compiled["status"].startswith("SUPERSEDED_FOR_EXECUTION"), compiled
assert compiled["execution_authority"] is False
assert compiled["promotion_authority"] is False

synthesis = next(a for a in hypergraph["actions"] if a["id"] == "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA")
unsatisfied = sorted(p["id"] for p in synthesis["preconditions"] if p.get("satisfied") is False)
expected = sorted([
    "SYNTHESIS_MATCHED_TARGET_SCOPE_DISCHARGE_AVAILABLE",
    "SYNTHESIS_MATCHED_QUALITY_AND_NONINFERIORITY_BINDINGS_INDEPENDENT_PASS",
])
assert unsatisfied == expected, unsatisfied
assert compiled["invalidation"]["synthesis_action_state"] == "BLOCKED_PRECONDITIONS"
assert sorted(compiled["invalidation"]["synthesis_unsatisfied_preconditions"]) == expected

assert scheduling["status"].startswith("ACTIVE_INDEPENDENT_PASS"), scheduling["status"]
assert scheduling["frontier"]["path"] == "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
assert scheduling["action_hypergraph"]["path"] == "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"

assert proof_atoms["status"].startswith("ACTIVE_INDEPENDENT_PASS"), proof_atoms["status"]
assert proof_atoms["expected_projection"]["canonical_leaf_atoms"] == 40
assert abductive["status"].startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"), abductive["status"]

assert authority["next"].startswith("RUN_CURRENT_TERMINAL_COVERAGE_PARTITION_V3__")
assert authority["next"] == authority["next_terminal_action"]
assert "30_CURRENT_TRUTHS" in authority["next"]
assert "DIRECT_EXTERNAL_EVIDENCE_LAST" in authority["next"]

historical_directive = compiled["execution_facing_authority"]["directive"]
assert historical_directive != authority["next"]
assert "RUN_ABDUCTIVE_WEAKEST_SUFFICIENT_RESIDUAL_COMPILATION" in historical_directive
assert "OTHER_40_CANONICAL_LEAF_ATOMS" in historical_directive
assert "NO_FRESH_REALITY_UNTIL_MINIMUM_REALITY_CUT" in historical_directive
assert compiled["execution_facing_authority"]["abductive_residual_theorem"] == "canonical/governance/ABDUCTIVE_RESIDUAL_THEOREM_ACTIVATION_V1.json"

print("test_current_authority_scheduler_generation_v2: PASS")
