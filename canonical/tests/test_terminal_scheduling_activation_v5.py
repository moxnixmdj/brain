import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def git_blob_sha(rel):
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

activation = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V5.json")
frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
v4_ver = load("canonical/verification/DELETED_PRIVATE_BAR_SUBSTITUTION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
hg_ver = load("canonical/verification/ACTION_HYPERGRAPH_V2_RECONCILIATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

assert activation["frontier"]["git_blob_sha"] == git_blob_sha("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
assert activation["action_hypergraph"]["git_blob_sha"] == git_blob_sha("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
assert v4_ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert hg_ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")

assert len(frontier["unresolved_predicates"]) == 31
assert len(frontier["certificates"]) == 17

covered = set()
for action in hypergraph["actions"]:
    covered.update(action.get("target_predicates", []))
assert set(frontier["unresolved_predicates"]) <= covered

forbidden_actions = {
    "DISCOVER_AND_BIND_FRONTIERCODE_CURSORBENCH_ROUTES",
    "BIND_PROFESSIONAL_AND_AA_BRIEFCASE_PUBLIC_ROUTES",
    "BIND_FINANCE_PUBLIC_BAR_ROUTES",
    "BIND_MYSTERYMECHANISM_PUBLIC_ROUTE",
}
assert not ({a["id"] for a in hypergraph["actions"]} & forbidden_actions)

assert activation["projected_state"]["unresolved_predicates"] == 31
assert activation["projected_state"]["certificate_candidates"] == 17
assert activation["projected_state"]["action_coverage_predicates"] == 31
assert activation["projected_state"]["deleted_private_execution_routes_resurrected"] == 0
assert activation["projected_state"]["reopened_scope_predicates_with_action_edges"] == 2

assert activation["new_reality_units_consumed"] == 0
assert activation["capability_credit_delta"] == 0
assert activation["family_credit_delta"] == 0
assert activation["execution_authority"] is False
assert activation["promotion_authority"] is False

print("test_terminal_scheduling_activation_v5: PASS")
