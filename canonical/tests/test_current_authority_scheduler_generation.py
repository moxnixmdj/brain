import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
scheduling = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
proof_atoms = load("canonical/governance/CANONICAL_PROOF_ATOM_BASIS_ACTIVATION_V1.json")

compiled = authority["compiled_next_frontier"]
assert compiled["status"].startswith("SUPERSEDED_FOR_EXECUTION"), compiled
assert compiled["execution_authority"] is False
assert compiled["promotion_authority"] is False

synthesis = next(a for a in hypergraph["actions"] if a["id"] == "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA")
unsatisfied = sorted(p["id"] for p in synthesis["preconditions"] if p.get("satisfied") is False)
assert unsatisfied == sorted([
    "SYNTHESIS_MATCHED_TARGET_SCOPE_DISCHARGE_AVAILABLE",
    "SYNTHESIS_MATCHED_QUALITY_AND_NONINFERIORITY_BINDINGS_INDEPENDENT_PASS",
]), unsatisfied
assert compiled["invalidation"]["synthesis_action_state"] == "BLOCKED_PRECONDITIONS"
assert sorted(compiled["invalidation"]["synthesis_unsatisfied_preconditions"]) == unsatisfied

assert scheduling["status"].startswith("ACTIVE_INDEPENDENT_PASS"), scheduling["status"]
assert scheduling["frontier"]["path"] == "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
assert scheduling["action_hypergraph"]["path"] == "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"

assert proof_atoms["status"].startswith("ACTIVE_INDEPENDENT"), proof_atoms["status"]
assert proof_atoms["expected_projection"]["canonical_leaf_atoms"] == 40
assert "INDEX_EXISTING_CONTENT_ADDRESSED_RECEIPTS_AGAINST_40_CANONICAL_LEAF_PROOF_ATOMS" in authority["next"]
assert "SKIP_EXHAUSTED_SYNTHESIS_PATH_UNLESS_ADMISSIBLE_INPUT_CHANGES" in authority["next"]

print("test_current_authority_scheduler_generation: PASS")
