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


frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V4.json")
hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
routes = load("canonical/governance/ZERO_COST_EVALUATION_ROUTE_MATRIX_V1.json")
recon = load("canonical/governance/DELETED_PRIVATE_BAR_STRONGER_PROOF_RECONCILIATION_V1.json")
verification = load(
    "canonical/verification/ACTION_HYPERGRAPH_V2_RECONCILIATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
)
activation_v5 = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V5.json")

assert verification["status"].startswith(
    "INDEPENDENT_PUBLIC_RUNNER_PASS__31_OF_31_ACTION_COVERAGE"
)
assert verification["public_runner"]["conclusion"] == "success"
assert (
    verification["exact_brain_blobs"][
        "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V4.json"
    ]
    == git_blob_sha("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V4.json")
)

historical_hypergraph_sha = verification["exact_brain_blobs"][
    "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"
]
assert activation_v5["action_hypergraph"]["git_blob_sha"] == historical_hypergraph_sha

assert (
    git_blob_sha("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
    != historical_hypergraph_sha
)

assert frontier["capability_credit_delta"] == 0
assert frontier["family_credit_delta"] == 0
assert hypergraph["capability_credit_delta"] == 0
assert hypergraph["family_credit_delta"] == 0

forbidden = {
    "DISCOVER_AND_BIND_FRONTIERCODE_CURSORBENCH_ROUTES",
    "BIND_PROFESSIONAL_AND_AA_BRIEFCASE_PUBLIC_ROUTES",
    "BIND_FINANCE_PUBLIC_BAR_ROUTES",
    "BIND_MYSTERYMECHANISM_PUBLIC_ROUTE",
}
ids = {a["id"] for a in hypergraph["actions"]}
assert not (ids & forbidden), ids & forbidden

required_substitutions = {
    "BUILD_CODING_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
    "BUILD_AA_BRIEFCASE_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
    "BUILD_FINANCE_AGENT_V2_DELETED_PRIVATE_BAR_STRONGER_PROOF",
    "BUILD_MYSTERYMECHANISM_DELETED_PRIVATE_BAR_STRONGER_PROOF",
}
assert required_substitutions <= ids

deleted = set(routes["summary"]["deleted_route_names"])
assert deleted == {
    "FrontierCode 1.1 Main",
    "CursorBench 4.0",
    "AA-Briefcase v1.1",
    "Finance Agent v2",
    "Vals MysteryMechanism",
}

for action in hypergraph["actions"]:
    if action["id"] in required_substitutions:
        assert action["action_class"] == "STRONGER_PROOF_SUBSTITUTION"
        assert action["new_reality_units"] == 0

assert recon["execution_authority"] is False
assert recon["promotion_authority"] is False

print("test_action_hypergraph_v2_reconciliation: PASS")
