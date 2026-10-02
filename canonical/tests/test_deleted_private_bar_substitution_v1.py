import json
from pathlib import Path

from canonical.runtime.terminal_certificate_cut_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V4.json")
recon = load("canonical/governance/DELETED_PRIVATE_BAR_STRONGER_PROOF_RECONCILIATION_V1.json")
routes = load("canonical/governance/ZERO_COST_EVALUATION_ROUTE_MATRIX_V1.json")
registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")

assert recon["capability_credit_delta"] == 0
assert recon["family_credit_delta"] == 0
assert recon["execution_authority"] is False
assert recon["promotion_authority"] is False

deleted = set(routes["summary"]["deleted_route_names"])
assert deleted == {
    "FrontierCode 1.1 Main",
    "CursorBench 4.0",
    "AA-Briefcase v1.1",
    "Finance Agent v2",
    "Vals MysteryMechanism",
}, deleted

frozen = {row["id"] for row in registry["predicates"]}
required_predicates = {
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_CURSORBENCH_GE_57_8",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "FINANCE_AGENT_V2_GE_58_59",
    "MYSTERYMECHANISM_GE_49_55",
}
assert required_predicates <= frozen
assert required_predicates <= set(frontier["unresolved_predicates"])

old_ids = {
    "CODING_FRONTIER_PUBLIC_ROUTE_CERTIFICATE",
    "PROFESSIONAL_ARTIFACT_PUBLIC_ROUTE_CERTIFICATE",
    "FINANCE_PUBLIC_ROUTE_CERTIFICATE",
    "MYSTERYMECHANISM_PUBLIC_ROUTE_CERTIFICATE",
}
ids = {row["id"] for row in frontier["certificates"]}
assert not (old_ids & ids), old_ids & ids

new_ids = {
    "CODING_PRIVATE_BAR_STRONGER_PROOF_CERTIFICATE",
    "GDPVAL_PUBLIC_ROUTE_CERTIFICATE",
    "AA_BRIEFCASE_STRONGER_PROOF_CERTIFICATE",
    "FINANCE_ACCOUNTING_INDEX_PUBLIC_ROUTE_CERTIFICATE",
    "FINANCE_AGENT_V2_STRONGER_PROOF_CERTIFICATE",
    "MYSTERYMECHANISM_STRONGER_PROOF_CERTIFICATE",
}
assert new_ids <= ids

for row in frontier["certificates"]:
    if row["id"] in {
        "CODING_PRIVATE_BAR_STRONGER_PROOF_CERTIFICATE",
        "AA_BRIEFCASE_STRONGER_PROOF_CERTIFICATE",
        "FINANCE_AGENT_V2_STRONGER_PROOF_CERTIFICATE",
        "MYSTERYMECHANISM_STRONGER_PROOF_CERTIFICATE",
    }:
        assert row["certificate_class"] == "STRONGER_PROOF_SUBSTITUTION"
        assert all("ROUTE_BOUND" not in req for req in row["requires"]), row

out = evaluate(frontier)
assert out["status"] == "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED", out
assert out["unresolved_predicate_count"] == 31, out
assert out["certificate_candidate_count"] == 17, out
assert out["covered_predicate_count"] == 31, out
assert out["uncovered_predicates"] == [], out
assert out["selected_certificate_count"] == 17, out
assert out["selected_new_reality_units"] == 0, out
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print("test_deleted_private_bar_substitution_v1: PASS")
