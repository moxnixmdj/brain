import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V4.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
routes = load("canonical/governance/ZERO_COST_EVALUATION_ROUTE_MATRIX_V1.json")
recon = load("canonical/governance/DELETED_PRIVATE_BAR_STRONGER_PROOF_RECONCILIATION_V1.json")

assert frontier["capability_credit_delta"] == 0
assert frontier["family_credit_delta"] == 0
assert hypergraph["capability_credit_delta"] == 0
assert hypergraph["family_credit_delta"] == 0

unresolved = set(frontier["unresolved_predicates"])
covered = set()
for action in hypergraph["actions"]:
    covered.update(action.get("target_predicates", []))
assert unresolved <= covered, sorted(unresolved - covered)

forbidden = {
    "DISCOVER_AND_BIND_FRONTIERCODE_CURSORBENCH_ROUTES",
    "BIND_PROFESSIONAL_AND_AA_BRIEFCASE_PUBLIC_ROUTES",
    "BIND_FINANCE_PUBLIC_BAR_ROUTES",
    "BIND_MYSTERYMECHANISM_PUBLIC_ROUTE",
}
ids = {a["id"] for a in hypergraph["actions"]}
assert not (ids & forbidden), ids & forbidden

required = {
    "BUILD_CODING_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
    "BUILD_AA_BRIEFCASE_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
    "BUILD_FINANCE_AGENT_V2_DELETED_PRIVATE_BAR_STRONGER_PROOF",
    "BUILD_MYSTERYMECHANISM_DELETED_PRIVATE_BAR_STRONGER_PROOF",
    "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
    "BUILD_DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
}
assert required <= ids

deleted = set(routes["summary"]["deleted_route_names"])
assert deleted == {
    "FrontierCode 1.1 Main",
    "CursorBench 4.0",
    "AA-Briefcase v1.1",
    "Finance Agent v2",
    "Vals MysteryMechanism",
}

for action in hypergraph["actions"]:
    if action["id"] in {
        "BUILD_CODING_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
        "BUILD_AA_BRIEFCASE_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
        "BUILD_FINANCE_AGENT_V2_DELETED_PRIVATE_BAR_STRONGER_PROOF",
        "BUILD_MYSTERYMECHANISM_DELETED_PRIVATE_BAR_STRONGER_PROOF",
    }:
        assert action["action_class"] == "STRONGER_PROOF_SUBSTITUTION"
        assert action["new_reality_units"] == 0

tool = [a for a in hypergraph["actions"] if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in a.get("target_predicates", [])]
deleg = [a for a in hypergraph["actions"] if "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" in a.get("target_predicates", [])]
assert len(tool) >= 1, tool
assert len(deleg) >= 1, deleg

assert recon["execution_authority"] is False
assert recon["promotion_authority"] is False

print("test_action_hypergraph_v2_reconciliation: PASS")
