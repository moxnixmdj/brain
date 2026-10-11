import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git_blob_sha(rel):
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


activation = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V5.json")
frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
v4_ver = load(
    "canonical/verification/DELETED_PRIVATE_BAR_SUBSTITUTION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
)
hg_ver = load(
    "canonical/verification/ACTION_HYPERGRAPH_V2_RECONCILIATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
)

# V5 is an immutable historical candidate. Its frontier bytes are still present.
assert (
    activation["frontier"]["git_blob_sha"]
    == git_blob_sha("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
)

# Its V2 action graph was independently verified at the exact historical blob.
historical_hypergraph_sha = hg_ver["exact_brain_blobs"][
    "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"
]
assert activation["action_hypergraph"]["git_blob_sha"] == historical_hypergraph_sha
assert hg_ver["public_runner"]["conclusion"] == "success"
assert v4_ver["public_runner"]["conclusion"] == "success"

# The path now contains later scheduler bytes. That makes V5 historical; it
# must not be reinterpreted as a live activation over today's graph.
assert (
    git_blob_sha("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
    != historical_hypergraph_sha
)
assert activation["status"].startswith("CANDIDATE_JOINT_ACTIVATION__31_PREDICATES")

assert len(frontier["unresolved_predicates"]) == 31
assert len(frontier["certificates"]) == 17
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
